
def run_workflow_until_approval(doc_text, uploaded_paths=None):

    uploaded_paths = uploaded_paths or []

    try:
        cred = DefaultAzureCredential()

        client = AIProjectClient(
            endpoint=ENDPOINT,
            credential=cred
        )

        with client:

            oc = client.get_openai_client()

            # 1. Upload documents to Foundry Vector Store
            vs_id = None

            if uploaded_paths:

                vs = oc.vector_stores.create(
                    name="Invoice-Processing"
                )

                vs_id = vs.id

                for path in uploaded_paths:

                    if path and Path(path).exists():

                        with open(path, "rb") as fh:

                            oc.vector_stores.files.upload_and_poll(
                                vector_store_id=vs_id,
                                file=fh
                            )

            # 2. Create Foundry conversation
            conv = oc.conversations.create()

            # 3. Process streaming events
            def process_stream(stream):

                all_text = []
                last_text_index = 0
                last_completed_action_id = None
                saw_approval_question = False

                for event in stream:

                    # Capture generated text
                    if event.type == ResponseStreamEventType.RESPONSE_OUTPUT_TEXT_DELTA:

                        d = getattr(event, "delta", "") or ""
                        all_text.append(d)

                    elif event.type == ResponseStreamEventType.RESPONSE_OUTPUT_TEXT_DONE:

                        t = getattr(event, "text", "") or ""

                        if t:
                            all_text.append(t)

                    # Detect workflow action started
                    elif event.type == ResponseStreamEventType.RESPONSE_OUTPUT_ITEM_ADDED:

                        if (
                            hasattr(event, "item")
                            and getattr(event.item, "type", None) == "workflow_action"
                        ):

                            aid = getattr(event.item, "action_id", None)

                            if aid:
                                last_text_index = len(all_text)

                                if aid == "approval-question":
                                    saw_approval_question = True

                                print(f"Started: {aid}")

                    # Detect workflow action completed
                    elif event.type == ResponseStreamEventType.RESPONSE_OUTPUT_ITEM_DONE:

                        if (
                            hasattr(event, "item")
                            and getattr(event.item, "type", None) == "workflow_action"
                        ):

                            aid = getattr(event.item, "action_id", None)

                            if aid:

                                last_completed_action_id = aid

                                step_text = "".join(
                                    all_text[last_text_index:]
                                ).strip()

                                summary = _extract_step_summary(
                                    aid,
                                    step_text
                                )

                                print(f"Completed: {aid}")
                                print(summary["summary"])

                                last_text_index = len(all_text)

                    # Handle errors
                    elif event.type == ResponseStreamEventType.ERROR:

                        raise Exception(
                            str(getattr(event, "error", None) or event)
                        )

                # Check if approval is needed
                full = "".join(all_text)

                waiting = (
                    saw_approval_question
                    or last_completed_action_id == "invoke-risk-scorer"
                    or (
                        "APPROVE" in full.upper()
                        and "REJECT" in full.upper()
                    )
                )

                return waiting, full

            # 4. Start workflow
            stream1 = oc.responses.create(
                conversation=conv.id,
                extra_body={
                    "agent": {
                        "name": WORKFLOW_NAME,
                        "type": "agent_reference"
                    }
                },
                input="Start",
                stream=True,
                metadata={"x-ms-debug-mode-enabled": "1"}
            )

            process_stream(stream1)

            # 5. Send documents
            stream2 = oc.responses.create(
                conversation=conv.id,
                extra_body={
                    "agent": {
                        "name": WORKFLOW_NAME,
                        "type": "agent_reference"
                    }
                },
                input=doc_text,
                stream=True,
                metadata={"x-ms-debug-mode-enabled": "1"}
            )

            waiting, response_text = process_stream(stream2)

            # 6. Return result
            return {
                "conversation_id": conv.id,
                "status": "waiting" if waiting else "complete",
                "response": response_text,
                "vector_store_id": vs_id
            }

    except Exception as e:

        return {
            "status": "error",
            "message": str(e)
        }
