- **Breaking:** SendGrid Email fails the run when an attachment is over 10 MB or the attachments
  total over 30 MB. It used to set `status` to the error and finish normally, so downstream nodes ran
  as if the email had been handled. Shrink the attachments to stay under the limits.
  [#3](https://github.com/griptape-ai/griptape-nodes-library-sendgrid/issues/3)
