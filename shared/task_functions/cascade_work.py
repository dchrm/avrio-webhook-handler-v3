import json
import logging
import re
from shared.services.karbon_services import Entities, Notes
import os
from datetime import datetime, timezone

# function to read the supplied json and supplied work item json package and add the next work
def main(this_work_item_json):
    """Reads the work item and extracts the Json to add the next work item in line"""
    
    entities_api = Entities(os.environ['KARBON_BEARER_TOKEN'], os.environ['KARBON_ACCESS_KEY'])
    notes_api = Notes(os.environ['KARBON_BEARER_TOKEN'], os.environ['KARBON_ACCESS_KEY'])

    # get this work item json from description field
    this_work_item_description_json = entities_api.extract_json_from_description(this_work_item_json['Description'])

    for this_trigger in this_work_item_description_json['followOnWorkItems']:

        # check if next work item has already triggered
        if this_trigger['isTriggered']:
            return
        
        # check if this work item status matches the trigger status for the next work item
        if this_trigger['statusForNextWorkToTrigger'] != this_work_item_json['WorkStatus']:
            return
        
        # get next work item template details
        next_work_item_template = entities_api.get(f"WorkTemplates/{this_trigger['nextWorkTemplateKey']}")
        next_work_item_template_description_json = entities_api.extract_json_from_description(next_work_item_template['Description'])



        # Pass this work item information to next work item JSON element
        ## If takeTitleFromUpstream is true, then use this work item title as the base for the next work item title
        ## If takeTitleFromUpstream is false, then leave the new work item base name in place for the next work item title
        if next_work_item_template_description_json['details']['takeTitleFromUpstream']:
            next_work_item_template_description_json['details']['thisTemplateNameBase'] = this_work_item_description_json['details']['thisTemplateNameBase']

        ## pass the period from one work item to the next.
        next_work_item_template_description_json['details']['thisWorkItemPeriod'] = this_work_item_description_json['details']['thisWorkItemPeriod']

        ## pass this work item key and title to the next work item description json
        next_work_item_template_description_json['details']['associatedWork'].append({"WorkItemKey": this_work_item_json['WorkItemKey'], "Title": this_work_item_json['Title']})

        # populate and restringify the next work item description
        ## convert the next work item description json to a string
        next_work_item_json_str = json.dumps(next_work_item_template_description_json, indent=2)
        ## update the next work item description with the next work item json
        updated_next_work_item_description = re.sub(
            r'\[JSON\].*?\[/JSON\]',
            f"[JSON]{next_work_item_json_str}[/JSON]",
            next_work_item_template['Description'],
            flags=re.DOTALL
        )

        # body for adding next work item
        next_work_item_json_body = {
            "AssigneeEmailAddress": this_work_item_json['AssigneeEmailAddress'],
            "Title": next_work_item_template_description_json['details']['thisWorkItemPeriod'] + " " + next_work_item_template_description_json['details']['thisTemplateNameBase'] + " " + next_work_item_template_description_json['details']['thisTemplateNameStatus'],
            "ClientKey": this_work_item_json['ClientKey'],
            "ClientType": this_work_item_json['ClientType'],
            "RelatedClientGroupKey": this_work_item_json['RelatedClientGroupKey'],
            "DueDate": this_work_item_json['DueDate'],
            "DeadlineDate": this_work_item_json['DeadlineDate'],
            "WorkTemplateKey": this_trigger['nextWorkTemplateKey'],
            "Description": updated_next_work_item_description,
            "StartDate": datetime.now(timezone.utc).isoformat(timespec='seconds')
        }

        # add next work item
        next_work_item = entities_api.post("WorkItems", next_work_item_json_body)

        # append next work item key to list of associate work items
        this_work_item_description_json['details']['associatedWork'].append({"WorkItemKey": next_work_item['WorkItemKey'], "Title": next_work_item['Title']})
        
        # update this work item json with the next work item key
        this_trigger['isTriggered'] = True
        this_trigger['resultingWorkItemKey'] = next_work_item['WorkItemKey']
        this_trigger['triggeredDateTime'] = datetime.now().isoformat()


        # update the the status of this work item after the trigger.
        this_work_item_json['WorkStatus'] = this_trigger['statusForThisWorkAfterTrigger']

        # update this work item description
        updated_this_work_item_description = re.sub(
            r'\[JSON\].*?\[/JSON\]',
            f"[JSON]{json.dumps(this_work_item_description_json, indent=2)}[/JSON]",
            this_work_item_json['Description'],
            flags=re.DOTALL
        )

        # reload the updated description to the original body
        this_work_item_json['Description'] = updated_this_work_item_description

        # put this work item back to Karbon
        this_work_item_updated = entities_api.put(f"WorkItems/{this_work_item_json['WorkItemKey']}", this_work_item_json)

        # add note to all associated work items
        ## Start the note body
        note_body = """"
        <p>The following work items are associated through a cascading work flow:</p><ol>
        """
        ## Start the timelines json with this work item key
        timelines = [{"entityKey": this_work_item_json['WorkItemKey'], "entityType": "WorkItem"}]
        ## add links to all associated work items so far
        for associated_work in this_work_item_description_json['details']['associatedWork']:
            note_body += f"<li><a href='https://app2.karbonhq.com/WorkItems/{associated_work['WorkItemKey']}'>{associated_work['Title']}</a></li>"
            
            # append associated timelines
            timelines.append({"entityKey": associated_work['WorkItemKey'], "entityType": "WorkItem"})
        
        ## add current work item to the list of associated work items
        note_body += f"<li><a href='https://app2.karbonhq.com/WorkItems/{this_work_item_json['WorkItemKey']}'>{this_work_item_json['Title']}</a></li></ol>"
        ## add the note to all associated work items

        logging.info(json.dumps(associated_work, indent=2))

        note = notes_api.add_note(
            "Work Item Triggered",
            note_body,
            timelines,
            this_work_item_json['AssigneeEmailAddress']
        )
                
        return this_work_item_updated
