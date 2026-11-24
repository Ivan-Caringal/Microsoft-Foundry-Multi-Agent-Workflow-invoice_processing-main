#collect input pass to the agent pass output

I recommend understanding this code by following how one invoice travels from the frontend to Microsoft Foundry and back to the frontend.

Don't try to understand all 600+ lines at once. The code becomes much easier when you understand its architecture first.
1. Understand the overall architecture
Your application has three major components:
1. Frontend — HTML / JavaScript

User uploads Invoice, PO, and GRN. Displays workflow progress and approval buttons.

HTTP Requests / SSE

2. Backend — Python / Flask

Receives documents, manages sessions, calls Foundry, monitors execution, and handles approvals.

Azure AI Projects SDK

3. Microsoft Foundry

Executes your existing Invoice-Processing-Workflow and its AI agents/actions.


Think of Python as the middleman connecting your frontend and Microsoft Foundry.
2. Understand the code in this order
Here is the order I recommend studying it.

RECOMMENDED LEARNING ORDER
1. Flask configuration and imports
   
   Start here:
   app = Flask(    __name__,    static_folder=str(PORTAL_DIR),    static_url_path="")
   
   
   
   Understand:
   - What Flask is.
   - What @app.route() does.
   - What an API endpoint is.
   - GET vs POST.
   This helps you understand how the frontend communicates with Python.
2. Session management
   
   Study:
   sessions = {}sessions_lock = threading.Lock()
   
   
   
   Understand:
   - What a session is.
   - Why you need a session_id.
   - Why events are stored in a dictionary.
   - Why threading locks are used.
   Each invoice upload gets its own session to track its workflow.
3. Document upload — api_upload()
   Start here first
   Study:
   @app.route("/api/upload", methods=["POST"])def api_upload():
   
   
   
   Understand the sequence:
   1. Receive files from frontend using request.files.
   2. Generate a unique session ID.
   3. Save the uploaded documents.
   4. Create a session in sessions.
   5. Start a background thread.
   6. Return the session ID to the frontend.
   This is the entry point of your entire application.
4. Microsoft Foundry integration
   
   Study:
   def run_workflow_until_approval(    session_id, doc_text, uploaded_paths=None):
   
   
   
   This is one of the most important functions.
   
   Understand:
   - DefaultAzureCredential()
   - AIProjectClient()
   - get_openai_client()
   - Vector store creation and document uploads.
   - oc.conversations.create()
   - oc.responses.create()
   This is where Python actually connects to and triggers your Foundry workflow.
5. Streaming workflow events — stream_and_emit()
   
   Understand:
   for event in stream:
   
   
   
   Python listens to Foundry events to determine:
   - Which workflow action started.
   - Which action completed.
   - Whether an error occurred.
   - Whether the workflow is waiting for approval.
   It then calls emit() to save progress.
6. Frontend progress — api_progress()
   
   Understand:
   @app.route("/api/progress/<session_id>")
   
   
   
   This uses Server-Sent Events (SSE).
   
   It continuously sends stored progress events from Python to the frontend so the user can see the workflow executing.
7. Approval and rejection
   
   Study these functions:
   api_approve()_run_approval_background()run_workflow_approval()
   
   
   
   Understand how the user's APPROVE or REJECT decision gets sent back to the same Foundry conversation.
8. Status and cleanup
   
   Finally, study:
   api_status()cleanup_foundry_data()_extract_step_summary()
   
   
   
   These handle status checking, deleting temporary Foundry files, and preparing readable workflow summaries.
3. Understand the complete execution flow
This is the most important diagram to remember.








medium.com


USER UPLOADS DOCUMENTS
        |
        v
POST /api/upload
        |
        v
Python saves Invoice, PO, GRN
        |
        v
Creates session_id
        |
        v
Starts background thread
        |
        v
run_workflow_until_approval()
        |
        v
Connects to Microsoft Foundry
        |
        v
Uploads files to Vector Store
        |
        v
Creates Foundry Conversation
        |
        v
Triggers Invoice-Processing-Workflow
        |
        v
Receives streaming events
        |
        v
emit() stores progress
        |
        v
GET /api/progress/<session_id>
        |
        v
Frontend displays progress
        |
        v
WAITING FOR APPROVAL
        |
        v
User clicks APPROVE or REJECT
        |
        v
POST /api/approve/<session_id>
        |
        v
Python sends decision to Foundry
        |
        v
Workflow continues and completes


4. Important Python concepts you should learn
You don't need to master everything before understanding this application.
Concept	Where it is used
Functions	run_workflow_until_approval()
Dictionaries	sessions = {}
Lists	events = []
HTTP requests	request.files
Flask routes	@app.route()
JSON	json.dumps()
Exception handling	try / except
Multithreading	threading.Thread()
Locks	threading.Lock()
Generators	yield in SSE
SDK integration	AIProjectClient()

5. My recommendation: Start with these 3 functions
Don't start with the Azure SDK yet. First understand how your backend works independently of Foundry.

Focus on these:
First
api_upload()

How does the backend receive documents from the frontend?


Second
emit()

How does the backend record workflow progress?


Third
run_workflow_until_approval()

How does Python connect to Microsoft Foundry and execute the workflow?


Once you understand those three, the remaining functions will make much more sense.

One important distinction: Your Python code does not implement the invoice extraction, matching, and risk-scoring AI logic itself. Those actions are executed by your configured Foundry workflow. Python orchestrates the interaction between the portal and Foundry.

My suggestion is that we study this like a code walkthrough: one function at a time, explaining every important line, what calls it, and what happens next. That way, you'll understand the actual application rather than just memorize Python syntax.