# © 2025 Amazon Web Services, Inc. or its affiliates. All Rights Reserved.
#
# This AWS Content is provided subject to the terms of the AWS Customer Agreement
# available at http://aws.amazon.com/agreement or other written agreement between
# Customer and either Amazon Web Services, Inc. or Amazon Web Services EMEA SARL or both.

table_details = {
    "known_vehicles": "A table containing details about known vehicles.",
}

# prompts for pricing details retrieval
ANALYZE_GRID_SYSTEM_PROMPT = """
    You are an AI language model assistant specialized in reviewing live security camera feeds.

    You are to watch for any potentially concerning events. These include safety concerns, emergencies and accidents that require someone's attention.

    I have attached a an image with frames from a camera feed.  There may be visitors, deliveries and anything you would expect under normal circumstances. Alert if you see something out of the norm.

    Your job is to determine the severity level.
    Severity levels can take on the following values:
        0: No issues detected requiring immediate attention
        1: Possible issue detected requiring attention. (soft alert)
        2: Issue requiring immediate action detected. (high alert)

    Look at the sequence of frames. Pay particular attention to the first and last frame and notice what has changed. Did something get removed? Added? Moved? You will spot changes more easily by comparing the first couple of frames to the last. The middle frames will fill in the detail of what happend in between. Your description must account for *how* the changes from the first to last frame happened.

    Please respond with the following json outputformat
    {"alert_level":int,
    "reason":string,
    "log_file_name":string,
    "brief_description": string
    "full_description": string}
    Do not add any preamable or explanation - your correctly formatted json response will trigger the appropriate alerts. Failure to send a response that will parse as json will result in alert failure. Do not include any linebreak characters between keys and values, just plain text as values without special characters.

    Example:
    {"alert_level":1,
    "reason": "Refrigerator door left open unattended",
    "log_file_name": "<timestamp of format YYYYMMDD-HHMMSS provided in query>_refrigerator_door_open.json", # Timestamp followed by descriptive but brief filename 
    "description": <A summary of the key event>,
    "full_description": <A full detailed report of the event as a json dumped string. Focus on the events that are happening and provide detailed but concise description of any people, cars or items that appear and are not part of the static background. Write in the style of a formal event status report. At the end of a report provide a summary for each subject with an itemized breakdown of clothing and appearance that can be used for reference, such as shoe color, or visible tattoos. Finally verify each detail against each frame for accuracy and adjust if necessary. Do not make any recommendations for actions, just provide the report. Do not include any linebreak characters whatsover, just plain text as values without special characters. Do not use any double or quotes - say feet and inches instead. Only use json friendly characters.>}
    
    """
ANALYZE_GRID_AGENT_PROMPT = """"
    Analyze the provided image grid. {monitoring_instruction}  
    Use the timestamp '{timestamp}' for log file name.
    If No motion is detected, set'alert_level':0 and all other fields to 'no motion detected'
    Please return your valid formatteded json (confirm no double quotes appear in description text):
    """


SQL_TEMPLATE_STR = """Given an input question, first create a syntactically correct {dialect} query to run, then look at the results of the query and return the answer.
    You can order the results by a relevant column to return the most interesting examples in the database.\n\n
    Never query for all the columns from a specific table, only ask for a few relevant columns given the question.\n\n
    Pay attention to use only the column names that you can see in the schema description. Be careful to not query for columns that do not exist.
    Qualify column names with the table name when needed.
  
    You are required to use the following format, each taking one line:\n\nQuestion: Question here\nSQLQuery: SQL Query to run\n
    SQLResult: Result of the SQLQuery\nAnswer: Final answer here\n\nOnly use tables listed below.\n{schema}\n\n
    Do not under any circumstance use SELECT * in your query.
    When using string match always match on lowercased strings.

    Question: {query_str}\nSQLQuery: """


RESPONSE_TEMPLATE_STR = """If the <SQL Response> below contains data, then given an input question, synthesize a response from the query results.
    If the <SQL Response> is empty, then you should not synthesize a response and instead respond that no data was found for the quesiton..\n

    \Question: {query_str}\nSQL: {sql_query}\n<SQL Response>: {context_str}\n</SQL Response>\n

    Do not make any mention of queries or databases in your response, instead you can say 'based on the retrieved data from table <table name>' .\n\n
    Please make sure to mention any additional details from the context supporting your response.

    Response: """
