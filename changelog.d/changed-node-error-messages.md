- SendGrid Email shows its own error message when a run fails, with the HTTP status and SendGrid's
  response under More info. A missing `SENDGRID_API_KEY` is reported first and on its own, with links
  to Settings and SendGrid's key page, and a refused key links to Settings. A missing `To Email`,
  `From Email` or content stops the node before it starts. Requires engine 0.105.0 or later.
  [#3](https://github.com/griptape-ai/griptape-nodes-library-sendgrid/issues/3)
