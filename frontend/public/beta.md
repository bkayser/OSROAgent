## What is OregonReferee.app?

I created OregonRefree.app as an experiment to help new referees, based on the simple proposition:

Which is a more frictionless support path for referees?

1. Telling them to send all the questions to the OSRO coordinator?
2. Creating a website with all the information they will need to know and asking them to go find answers there?
3. Creating a Chatbot that reads all that information instead, and tells you specifically what you ask?

Welcome to your Referee Concierge!

### How It Works

OregonReferee.app uses a specialized AI chatbot that utilizes a custom knowledge base. Unlike general-purpose AI, this tool is grounded in regional data to prevent generic or irrelevant answers.

* **Data Ingestion:** We ingest documentation from RefTown, OYSA, NWSC, and the Oregon Soccer Referee Organization. The full pipeline for how we add and manage this data is documented in our [README-ingest file](https://github.com/bkayser/OSROAgent/blob/main/README-ingest.md).
* **Certification Verification:** The bot can query public USSF data to provide real-time license expiration dates to referees, helping them stay compliant without administrative intervention.
* **Language Support:** It will give you an answer in the language of you question.  It supports any common foreign language.
* **Organizational Landscape:** You can see the list of common organizations that hire refs and display it all in a graphical view that shows how they relate to leagues.

### Deployment & Feedback

We are currently in the **Beta phase**. We invite administrators to stress-test the bot with league-specific queries.  Please use the *Feedback* link at the bottom of the page to let us know when information is missing or incorrect.  Use thumbs up or thumbs down to grade the responses.

If your specific league or tournament ROCs are not yet represented, we can ingest your documentation to expand the bot’s utility.

For a full look at the codebase and logic, please visit the [OSROAgent Repository](https://github.com/bkayser/OSROAgent/blob/main/README-ingest.md).

