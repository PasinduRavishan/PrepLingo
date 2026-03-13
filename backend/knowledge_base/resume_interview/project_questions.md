# Resume-Based Interview — How to Ask About Projects

## Interviewer Strategy for Resume-Based Questions

Resume-based interviews go DEEP on the candidate's actual experience.
The goal is to distinguish what they DID vs what they COPIED or SUPERVISED.

---

## Project Deep-Dive Framework

When a candidate mentions a project, move through these layers:

### Layer 1: What Did You Build?
- "Walk me through what this project does."
- "What problem does it solve?"
- "Who were the users?"

### Layer 2: What Was YOUR Role?
- "What were you specifically responsible for?"
- "Were you working solo or in a team? What was your team size?"
- "What decisions were you the owner of?"

### Layer 3: Why Did You Make These Technical Choices?
This is the MOST IMPORTANT layer. It separates copiers from builders.
- "Why did you choose [Technology X] over alternatives?"
- "What other technologies did you evaluate for [component]?"
- "Why [MongoDB/PostgreSQL/etc.] for the database?"
- "Why did you architect it this way?"

### Layer 4: How Does It Work Internally?
- "Explain how the [key feature] works under the hood."
- "How does data flow through your system?"
- "Walk me through a user request from start to finish."

### Layer 5: Challenges and Growth
- "What was the hardest part of building this?"
- "What bugs or production issues did you face?"
- "What would you do differently if you rebuilt it today?"
- "If you had to scale this to 10x users, what breaks first?"

---

## Tech Stack Probing Questions

### For Python Developers
- "Explain the difference between a list and a tuple in Python."
- "What is a generator and when would you use one?"
- "Explain Python's GIL and how it affects multithreading."
- "What is a decorator and write one from memory."

### For JavaScript/Node.js Developers
- "Explain the event loop."
- "What is the difference between `async/await` and Promises?"
- "What is closure and give an example from your project."
- "Explain how Node.js handles concurrent requests."

### For React Developers
- "Explain the difference between state and props."
- "When would you use `useCallback` vs `useMemo`?"
- "How does React's reconciliation algorithm work?"
- "Explain how you managed state in your project. Why that approach?"

### For Database Integration
- "How did you handle database connection pooling?"
- "Did you write raw SQL or use an ORM? Why?"
- "How did you handle database migrations?"
- "What indexes did you create and why?"

---

## Questions Based on Common CV Tech Stacks

### If CV mentions: MongoDB
- "How is data modeled in MongoDB differently from SQL?"
- "Explain the aggregation pipeline with an example from your project."
- "How did you handle data relationships without foreign keys?"
- "When would you NOT use MongoDB?"

### If CV mentions: Docker
- "What is the difference between a container and a VM?"
- "Explain how you wrote your Dockerfile."
- "How does Docker networking work?"
- "What would you put in .dockerignore and why?"

### If CV mentions: REST API / Backend
- "Explain REST principles and how your API follows them."
- "How did you handle authentication in your API?"
- "What HTTP status codes did you use and why?"
- "How did you handle errors consistently across endpoints?"

### If CV mentions: Machine Learning / AI
- "Explain bias-variance tradeoff."
- "How did you handle imbalanced datasets?"
- "How did you evaluate your model's performance? What metrics?"
- "What deployment challenges did you face?"

---

## Red Flag Indicators in Resume-Based Interviews

🚩 Can't explain WHY they chose a technology (just used it because tutorial used it)
🚩 Says "we did X" exclusively — never "I did X"
🚩 Can't describe data flow through their own system
🚩 Never encountered any bugs or challenges (not credible)
🚩 Can't reason about scaling their project
🚩 Lists technology but can't explain what it does
