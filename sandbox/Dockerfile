# This Dockerfile is only used with --profile test in order to exercise various network endpoints for load testing.
FROM grafana/k6:0.50.0

WORKDIR /app

# Copy your k6 test script to the container
COPY script.js script.js
COPY litellm litellm
COPY iapi iapi
COPY index.js index.js
# Run the k6 test using the copied script
CMD ["run", "script.js"]
