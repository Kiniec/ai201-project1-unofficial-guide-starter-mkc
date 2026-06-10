# The Unofficial Guide — Project 1

> **How to use this template:**
> Complete each section *after* you've built and tested the corresponding part of your system.
> Do not write placeholder text — if a section isn't done yet, leave it blank and come back.
> Every section below is required for submission. One-liners will not receive full credit.

---

## Domain

<!-- What topic or category of knowledge does your system cover?
     Why is this knowledge valuable, and why is it hard to find through official channels?
     Example: "Student reviews of CS professors at [university] — useful because official
     course descriptions don't reflect teaching style, exam difficulty, or workload." -->
This is the Unofficial guide for helping with students if they face homelessness or food shortages while in college. The need for this guide is necessary, due the fact more than 1.5 million college students are homeless during their collegiate career. The guide will answer question on where to obtain resources and services if needed.  
---

## Document Sources

<!-- List every source you collected documents from.
     Be specific: include URLs, subreddit names, forum thread titles, or file names.
     Aim for variety — sources that together cover different subtopics or perspectives. -->

| # | Source | Type | URL or location |
|---|--------|-------------|-----------------|
| 1 |UNT Dallas| Public University | https://www.untdallas.edu/finaid/apply/emergency-funding.php|
| 2 |Dallas Housing Authority | Government | https://dhantx.com/applicants/emergency-housing-resources/ |
| 3 |Salvation Army | Charity |https://salvationarmyntx.org/north-texas/carr-p-collins-social-service-center/provide-housing|
| 4 |Austin Street Center | Non-profit | https://austinstreet.org/wp-content/uploads/2024/12/ASC-Resource-Guide-2024.pdf |
| 5 | Dallaslife| Non-profit |https://dallaslife.org/place-to-stay/|
| 7 | Under 1 Roof| Non-profit | https://www.under1roofdallas.org/faq?questionId=0f50598c-e23b-4c41-9625-f4cb302a2547|
| 8 | Housing Forward| Non-profit| https://housingforwardntx.org|
| 9 |Inspired Vision Compassion Center | Non-profit | https://www.ivcompassion.org/|
| 10 |Hoy Trinity | Ministries |https://htdallas.org/ht-food-pantry/|
| 11 |UNT Denton| Public University |https://www.unt.edu/onestop/student-emergency-support-program.html |
| 12 |UNT Denton| Public University |https://studentaffairs.unt.edu/desresources/programs/food-pantry/hours.html |
| 13|UT Dallas | Public University |https://basicneeds.utdallas.edu/resource-hub/ |
| 14 |Dallas College | Public University  |https://www.dallascollege.edu/resources/student-care-network/housing/|
| 15 |UT Dallas | Public University |https://basicneeds.utdallas.edu/resource-hub/ |
| 16 | Reddit|Social Media |https://www.reddit.com/r/Dallas/comments/1hdmir3/help_with_the_unhoused/ |
| 17 |SchoolHouse Connection| Non-profit |https://schoolhouseconnection.org/article/tips-for-helping-homeless-youth-succeed-in-college |
| 18 |Reddit| Social Media Platform |https://www.reddit.com/r/college/comments/13ga1a0/any_students_here_that_are_homeless_or_live_out/ |
| 19 |Reddit| Social media Platform | https://www.reddit.com/r/homeless/comments/17ez9gv/places_to_sleep_in_dallas_general_tips_for/|
| 20 |Reddit| Social Medium Platform | https://www.reddit.com/r/college/comments/1o50k4v/homelessness_and_college/| 
| 10 |Medium | Blog |https://switchupcb.medium.com/7-tips-to-help-you-survive-while-homeless-274fc831b07f|

---

## Chunking Strategy

<!-- Describe your chunking approach with enough specificity that someone else could reproduce it.
     Include:
     - Chunk size (characters or tokens) and why that size fits your documents
     - Overlap size and why (or why not) you used overlap
     - Any preprocessing you did before chunking (e.g., stripping HTML, removing headers)
     - What your final chunk count was across all documents -->

**Chunk size:**
chunk_size = 300 tokens (ceiling — semantic splits take priority; 400t is the max fallback)
**Overlap:**
overlap = 50 tokens - Overlapping was utilized to ensure that information sitting at the boundary between two chunks isn't lost.
**Why these choices fit your documents:**
The chunk size and overlap fits my documents for natural content breaks across mixed sources (web pages, PDFs, Reddit threads). 300 token ceiling prevents oversized chunks when semantic boundaries are unclear and using overlap of 50 tokens preserves context across chunk boundaries for intact retrieval. Before chunking is engaged, stripping of HTML, javascript, footers, and headers must be performed. 

**Final chunk count:**
135 chunks 
---

## Embedding Model

<!-- Name the embedding model you used and explain your choice.
     Then answer: if you were deploying this system for real users and cost wasn't a constraint,
     what tradeoffs would you weigh in choosing a different model?
     Consider: context length limits, multilingual support, accuracy on domain-specific text,
     latency, and local vs. API-hosted. -->

**Model used:**
The model utilized for this project was all-MiniLM-L6-v2 via sentence-transformers for its speed, cost, sentencing and paragraphs capturing and low latency. 
**Production tradeoff reflection:**
For real-world applications, one should consider language support, domain-specific retrieval computing power, and storage and some latency. If cost wasn't a constraint, OPenAI(text-embedding-3-large) would be considered. It provides high versatility, performance and supports variable dimensions. The main trade-off of using model all-MiniLM-L6-v2, will be lower accuracy. 
---
---

## Grounded Generation

<!-- Explain how your system enforces grounding — how does it prevent the LLM from answering
     beyond the retrieved documents?
     Describe both your system prompt (what instruction you gave the model) and any structural
     choices (e.g., how you formatted the context, whether you filtered low-relevance chunks).
     Do not just say "I told it to use the documents" — show the actual instruction or explain
     the mechanism. -->

**System prompt grounding instruction:**
The system prevents the LLM from going beyond what is provided as resources from the prompt given. The instructions given to the model was to use only information in the provided urls and documents to answer questions. If the information is not located, a prompt will notify the user the sourced documents does not contain enough information for that response.
 **How source attribution is surfaced in the response:**
The responses are formatted with names of urls or documents in which the information was retrieved. The sources are cited and attached to the shown responses. 
---

## Evaluation Report

<!-- Run your 5 test questions from planning.md through your system and record the results.
     Be honest — a partially accurate or inaccurate result that you explain well is more
     valuable than a suspiciously perfect result. -->

| # | Question | Expected answer | System response (summarized) | Retrieval quality | Response accuracy |
|---|----------|-----------------|------------------------------|-------------------|-------------------|
| 1 |What colleges have emergency support for students?|UT Dallas, UNT Dent, UNT Dallas, Dallas College  |The system returned 3 colleges that have emergency support for students | Relevant | Partially accurate |
| 2 |What are the hours for the food pantry for Holly Trinity? | 9am-Noon| The system responded with the hours along the days the food pantry is in operation. | Relevant | Partially accurate|
| 3 |What are the intake hours for Dallas Life? | 1p.m. - 8p.m. | The system responded with intake hours 1pm - 8pm and mentioned showing up early and obtaining admission.| Relevant | Accurate| 
| 4 |What are the intake days for Dallas Life? | Monday - Friday| The system responded with the intake days of Monday and Friday. It also mentioned intake hours, with a number to call, and with whom to speak with. | Relevant |Accurate |
| 5 |Where can I get food from on the campus of UT Dallas |Comet Cupboard | The system responded with receiving food from the Comet Cupboard and note it is the onsite food pantry. It provided who can visit and the frequency of visits. | Relevant | Accurate|

**Retrieval quality:** Relevant / Partially relevant / Off-target  
**Response accuracy:** Accurate / Partially accurate / Inaccurate

---

## Failure Case Analysis

<!-- Identify at least one question where retrieval or generation did not work as expected.
     Write a specific explanation of *why* it failed, tied to a part of the pipeline.

     "The answer was wrong" is not an explanation.

     "The relevant information was split across a chunk boundary, so retrieval returned
     only half the context — the model didn't have enough to answer correctly" is an explanation.

     "The embedding model treated the professor's nickname as out-of-vocabulary and returned
     results from an unrelated review" is an explanation. -->

**Question that failed:**
What is building rotation when experiencing homelessness? 
**What the system returned:**
The system responded with information from other sources that were partially accurate.
**Root cause (tied to a specific pipeline stage):**
The root cause of the failure was an ingestion issue, which is the first stage of the pipeline. Content could not be ingested therefore anything downstream, chunking, retrieval, generation, would not see it. A function, fetch_web() failed on JavaScript and bot-blocked sites. 
**What you would change to fix it:**
To fix this issue, sites that can not be rendered by the function would need to be placed in a .txt file. 
---

## Spec Reflection

<!-- Reflect on how planning.md shaped your implementation.
     Answer both questions with at least 2–3 sentences each. -->

**One way the spec helped you during implementation:**
Relying on the specifications before implementing any code, allowed for a overview of the project. The planning document served as a guideline and blueprint to implement each step and expectations of the project. 
**One way your implementation diverged from the spec, and why:**
The implementation of the project diverged slightly from the planning by the functions to ingest, chunk, retrieve and generate.  Although it was not far off, the functions to complete project were similar in performance. 
---

## AI Usage

<!-- Describe at least 2 specific instances where you used an AI tool during this project.
     For each: what did you give the AI as input, what did it produce, and what did you
     change, override, or direct differently?

     "I used Claude to help me code" is not sufficient.
     "I gave Claude my Chunking Strategy section from planning.md and asked it to implement
     chunk_text(). It returned a function using a fixed character split. I overrode the
     chunk size from 500 to 200 because my documents are short reviews, not long guides." -->

**Instance 1**

- *What I gave the AI:*
Claude was given the the documents section to review for ingesting and chunking. 
- *What it produced:*
The function ingest_and_chunky() was produced to ingest content and provide chunking. 
- *What I changed or overrode:*
The function provided did not need to be overwritten or changed. It aided in the completion of the overall file.
**Instance 2**

- *What I gave the AI:*
For the query interface specifications was given to Claude to produce a web UI using Gradio. 
- *What it produced:*
Claude was able to create a file called app.py, which is a user friendly interface that instructions on how to navigate the user interface.  
- *What I changed or overrode:*
The UI theme was changed to a visually pleasing color. The specs 