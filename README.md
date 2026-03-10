# 🧠🌐 CodeAtlas

**AI that understands your entire codebase.**

CodeAtlas analyzes a repository and generates a **visual architecture map, dependency graph, and knowledge graph** so developers can instantly understand how complex systems work.

Instead of manually reading thousands of lines of code, CodeAtlas builds an **AI-powered structural understanding of the repository.**

---

## 🚀 Features

* 🧠 **AI Code Understanding**
  Parses the entire repository and builds a structural model.

* 🏗 **Architecture Map**
  Visualizes how modules, services, and layers connect.

* 🕸 **Dependency Graph**
  Displays file, package, and library dependencies.

* 🌐 **Code Knowledge Graph**
  Links functions, classes, modules, and interactions.

* ⚡ **Instant Repo Analysis**
  Upload a repository and generate insights in seconds.

* 🔎 **Developer Intelligence**

  * Detect tightly coupled modules
  * Find critical files
  * Understand system entry points

---

## 🧠 What It Generates

CodeAtlas converts a codebase into **three intelligent visual layers**:

### 1️⃣ Architecture Map

High-level system overview.

```
Frontend
   │
   ▼
API Layer
   │
   ▼
Services
   │
   ▼
Database
```

---

### 2️⃣ Dependency Graph

Shows how modules depend on each other.

```
auth.js ───► userService.js
userService.js ───► database.js
database.js ───► models.js
```

---

### 3️⃣ Knowledge Graph

A semantic map of the entire codebase.

```
UserController
   │
   ├── createUser()
   ├── loginUser()
   │
   ▼
AuthService
   │
   ▼
JWTModule
```

---

## ⚙️ How It Works

1. Repository is uploaded or cloned
2. Code parser analyzes files
3. AI extracts structure and relationships
4. Graph engine builds system maps
5. Interactive UI renders architecture and graphs

---

## 🛠 Tech Stack

**Backend**

* Node.js / Python
* AST parsers
* Graph generation

**AI Layer**

* Code embeddings
* semantic analysis
* repository reasoning

**Frontend**

* React
* D3.js / Graph visualization
* Interactive architecture viewer

---

## 📊 Example Use Cases

* Understand large open-source projects
* Onboard developers faster
* Analyze unfamiliar codebases
* Visualize system architecture
* Detect structural complexity

---

## 🎯 Vision

Modern codebases are too large to understand by reading files manually.

CodeAtlas transforms repositories into **interactive knowledge systems** where developers can explore architecture visually.

---

## 🧑‍💻 Author

**Krishna Shahane**

Self-taught developer building tools to explore systems, intelligence, and technology.

---

## ⭐ Support

If you find this project useful, give it a **star ⭐**.
