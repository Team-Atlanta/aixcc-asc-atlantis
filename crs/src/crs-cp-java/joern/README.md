# Joern Analysis Server

This Python server provides an API for static code analysis using Joern. It allows users to perform queries, execute scripts, and generate graph representations of codebases through HTTP requests.

## Requirements

- Python 3.6 or higher
- Joern installed and accessible from the command line


# Joern Server

Ensure Joern is properly installed and accessible from the command line.

## Running the Server

To start the server on the default port (8000), run:

```bash
python run-joern.py
```


## API Endpoints

### GET /

- **Description:** Returns a welcome message.
- **Response:**
  ```json
  {
    "message": "Hello, this is a GET request. Send a Joern query via POST."
  }
  ```

### POST /single_query

- **Description:** Runs a single Joern query.
- **Request Body:**
  ```json
  {
    "input": "path/to/code",
    "query": "joern query"
  }
  ```
- **Response:**
  ```json
  {
    "status": "success",
    "data": {...}
  }
  ```

### POST /script_query

- **Description:** Runs a Joern script with parameters.
- **Request Body:**
  ```json
  {
    "input": "path/to/code",
    "queryPath": "path/to/script",
    "param": {
      "param1": "value1",
      "param2": "value2"
    }
  }
  ```
- **Response:**
  ```json
  {
    "status": "success",
    "data": {...}
  }
  ```

### POST /graph_query

- **Description:** Exports the CPG graph to a specific format.
- **Request Body:**
  ```json
  {
    "input": "path/to/code"
  }
  ```
- **Response:**
  ```json
  {
    "status": "success",
    "data": "Graph exported successfully"
  }
  ```
