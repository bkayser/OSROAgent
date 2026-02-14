## What is OregonReferee.app?

Managing the sheer volume of procedural information—from RefTown self-assignment to varying league-specific emergency protocols—is a major barrier to referee retention and performance. **OregonReferee.app** provides an AI-powered solution to this fragmentation.

### How It Works

This application is a specialized AI chatbot that utilizes a custom knowledge base. Unlike general-purpose AI, this tool is grounded in regional data to prevent generic or irrelevant answers.

* **Data Ingestion:** We ingest documentation from RefTown, OYSA, NWSC, and the Oregon Soccer Referee Organization. The full pipeline for how we add and manage this data is documented in our [README-ingest file](https://github.com/bkayser/OSROAgent/blob/main/README-ingest.md).
* **Certification Verification:** The bot can query public USSF data to provide real-time license expiration dates to referees, helping them stay compliant without administrative intervention.

### Deployment & Feedback

We are currently in the **Beta phase**. We invite administrators to stress-test the bot with league-specific queries.

Please use the *Feedback* link at the bottom of the page to let us know when information is missing or incorrect.

* **Hallucinations:** In rare cases where information is missing, the AI may provide inaccurate answers. We are mitigating this through continuous training.
* **Expansion:** If your specific league or tournament ROCs are not yet represented, we can ingest your documentation to expand the bot’s utility.

For a full look at the codebase and logic, please visit the [OSROAgent Repository](https://github.com/bkayser/OSROAgent/blob/main/README-ingest.md).

