# Sandbox

The `sandbox` folder contains all of the test data and infrastructure code needed to standup the common services within a `CRS Sandbox` execution environment.
This is both for local development during development and at competition time.
dev
These services include the `iAPI` and the `LiteLLM` proxy.

We use Docker Compose Profiles to seperate `development` from `competition`.
This is how we disable the `LiteLLM` proxy container at competition time as this container WILL NOT have internet access in the constrained environment.

## DO NOT MAKE CHANGES WITHIN THIS FOLDER
