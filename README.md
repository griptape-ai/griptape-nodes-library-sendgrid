# SendGrid Email Node - Usage Examples

## Overview

The SendGrid Email Node allows you to send emails through the SendGrid API with support for:
- Plain text and HTML content
- Multiple attachment types (artifacts and legacy dict format)
- Smart MIME type handling (defaults for artifacts, detection for dict format)
- Smart size validation (10MB per attachment, 30MB total)
- Send toggle for testing
- Comprehensive debug logging
- Graceful error handling

## Prerequisites

**Note**: Dependencies are automatically managed when installing this Griptape node library. No manual installation required.

1. Get a SendGrid API key:
   - Sign up at [SendGrid](https://sendgrid.com/)
   - Create an API key in your SendGrid dashboard
   - Set the API key in your configuration under "SendGrid" → "SENDGRID_API_KEY"
   - Or set the `SENDGRID_API_KEY` environment variable

## Basic Usage

### Simple Text Email

```python
# Example parameter values:
to = "recipient@example.com"
from = "sender@yourdomain.com"
subject = "Hello from Griptape!"
text_content = "This is a simple text email sent via SendGrid."
send = True
```

### HTML Email

```python
# Example parameter values:
to = "recipient@example.com"
from = "sender@yourdomain.com"
subject = "HTML Newsletter"
html_content = """
<html>
<body>
    <h1>Welcome to our Newsletter!</h1>
    <p>This is an <strong>HTML email</strong> with rich formatting.</p>
    <ul>
        <li>Feature 1</li>
        <li>Feature 2</li>
        <li>Feature 3</li>
    </ul>
</body>
</html>
"""
send = True
```

### Email with Both Text and HTML Content

```python
# Example parameter values:
to = "recipient@example.com"
from = "sender@yourdomain.com"
subject = "Multi-format Email"
text_content = "This is the plain text version of the email."
html_content = "<html><body><h1>This is the HTML version</h1><p>Much prettier!</p></body></html>"
send = True
```

## Attachments

The SendGrid Email Node supports multiple attachment types with **smart MIME type handling**:

### Supported Artifact Types

- **TextArtifact** - Text files (.txt, documents)
- **ImageArtifact** - Image data (PNG, JPEG, etc.)
- **ImageUrlArtifact** - Images from URLs (automatically downloaded)
- **AudioArtifact** - Audio files (MP3, WAV, etc.)
- **VideoArtifact** - Video files (MP4, AVI, etc.) - includes local class definition
- **VideoUrlArtifact** - Videos from URLs (automatically downloaded)
- **Legacy Dict Format** - Manual attachment specification

### Size Limits

⚠️ **Important Size Restrictions:**
- **Individual attachment limit**: 10MB maximum per file
- **Total email limit**: 30MB maximum for all attachments combined
- Emails exceeding these limits will be **blocked** with clear error messages

### Using Artifact Types (Recommended)

```python
# Artifacts are automatically handled - just connect them to the attachments parameter
# The node will automatically:
# - Assign appropriate default MIME types
# - Validate file sizes
# - Encode content properly

# Examples of artifact connections:
# - Connect ImageArtifact from image generation nodes
# - Connect VideoUrlArtifact from video processing nodes  
# - Connect TextArtifact from text processing nodes
# - Mix multiple artifact types in a single email
```

### Legacy Dict Format (Still Supported)

For manual attachment specification:

```python
# Example parameter values:
to = "recipient@example.com"
from = "sender@yourdomain.com"
subject = "Email with Attachment"
text_content = "Please find the attached document."
attachments = [
    {
        "filename": "document.pdf",
        "content": "base64_encoded_pdf_content_here",  # Base64 encoded content
        "type": "application/pdf"  # MIME type (optional - detected from filename if not provided)
    }
]
send = True
```

### Multiple Mixed Attachments

```python
# Mix of artifact types and legacy format:
attachments = [
    # Legacy dict format
    {
        "filename": "report.pdf", 
        "content": "base64_encoded_pdf_content",
        "type": "application/pdf"
    },
    # Artifacts connected from other nodes automatically included
    # (ImageArtifact, VideoUrlArtifact, TextArtifact, etc.)
]
```

### MIME Type Handling

**Artifact Types (Default MIME Types):**
- **TextArtifact** → `text/plain`
- **ImageArtifact/ImageUrlArtifact** → `image/png` (default for all images)
- **AudioArtifact** → `audio/mpeg` (default for all audio)
- **VideoArtifact/VideoUrlArtifact** → `video/mp4` (default for all video)

**Legacy Dict Format (Advanced MIME Detection):**
- **User-specified**: Use the `type` field you provide
- **Filename-based**: Python's `mimetypes.guess_type()` detects from file extension
- **Fallback**: `application/octet-stream` if detection fails

### Other Automatic Features

✅ **Size Validation** - Prevents emails from failing due to size limits  
✅ **URL Download** - Automatically downloads content from ImageUrlArtifact and VideoUrlArtifact  
✅ **Error Handling** - Clear error messages for size violations or processing failures  
✅ **Mixed Types** - Combine different artifact types in a single email

## Testing Mode

Use the `send` parameter to disable email sending during testing:

```python
# For testing - email won't be sent
send = False
```

When `send=False`, the node will process all parameters and validate them, but won't actually send the email. This is useful for:
- Testing email content formatting
- Validating attachments
- Debugging parameter values

## Debug Logging

The node includes comprehensive debugging capabilities through a hidden `logs` output parameter:

### What's Logged:
- Parameter validation results
- API key status
- Email composition details  
- Attachment processing (type assignment, size validation, downloads)
- MIME type assignment results
- Size limit checks
- SendGrid API response details
- Error messages and detailed stack traces

### Accessing Debug Logs:
1. **Hidden by default** - The debug logs parameter is hidden to keep the UI clean
2. **Enable when needed** - Show the "Debug Logs" parameter in node properties for troubleshooting
3. **Comprehensive output** - Detailed step-by-step processing information
4. **Real-time updates** - Logs are updated throughout the email processing pipeline

### When to Use Debug Logs:
- Troubleshooting attachment processing issues
- Understanding size limit violations  
- Checking MIME type assignments
- Investigating SendGrid API responses
- General email sending troubleshooting

## Error Handling

The node provides robust error handling with graceful failure modes:

### Size Limit Violations (Graceful Handling):
- **Individual file > 10MB**: Email blocked, clear error message in status
- **Total email > 30MB**: Email blocked, clear error message in status  
- **No exceptions thrown** - Node completes successfully with error status
- **Detailed feedback** - Exact file sizes and limits shown in error messages

### Technical Errors (Exception Handling):
- Missing required parameters (to, from, content)
- Invalid API key
- SendGrid API errors
- Network connectivity issues
- Attachment download failures

### Error Reporting:
- **Status Parameter**: Clear, user-friendly error messages
- **Debug Logs**: Detailed technical information for troubleshooting
- **Graceful vs Exception**: Size violations are graceful, technical errors throw exceptions
- **Real-time Feedback**: Errors reported immediately during processing

### Example Error Messages:
```
❌ Attachment 'large_video.mp4' (15.67 MB) exceeds 10MB limit. Email processing aborted.
❌ Total email size (32.45 MB) exceeds 30MB limit. Email processing aborted.  
❌ Error sending email: Invalid API key
```

## Configuration

### Method 1: Griptape Configuration
Set the API key in your Griptape configuration:
- Section: "SendGrid"
- Key: "SENDGRID_API_KEY"
- Value: Your SendGrid API key

### Method 2: Environment Variable
```bash
export SENDGRID_API_KEY="your_sendgrid_api_key_here"
```

## Workflow Integration Examples

### Image Generation to Email
```
Image Generator → ImageArtifact → SendGrid Email
```
- Automatically handles image attachment with default MIME type (image/png)
- Size validation prevents oversized images from causing email failures

### Video Processing to Email  
```
Video Generator → VideoUrlArtifact → SendGrid Email
```
- Automatically downloads video from URL
- Validates size limits (10MB per file, 30MB total)
- Handles large video files gracefully with clear error messages

### Multi-Media Workflow
```
Image Node → ImageArtifact ↘
Text Node → TextArtifact → SendGrid Email → Success/Error Status
Video Node → VideoUrlArtifact ↗
```
- Mix multiple artifact types in single email
- Default MIME type assignment for each artifact type
- Comprehensive size validation across all attachments

## MIME Types Reference (For Dict Format)

When using the legacy dict format, you can specify these MIME types manually or let Python's `mimetypes.guess_type()` detect them from filenames:

- **Documents**: 
  - PDF: `application/pdf`
  - Word: `application/vnd.openxmlformats-officedocument.wordprocessingml.document`
  - Excel: `application/vnd.openxmlformats-officedocument.spreadsheetml.sheet`
  - PowerPoint: `application/vnd.openxmlformats-officedocument.presentationml.presentation`
  - CSV: `text/csv`
  - TXT: `text/plain`
- **Images**: 
  - JPEG: `image/jpeg`
  - PNG: `image/png`
  - GIF: `image/gif`
- **Media**: 
  - MP4: `video/mp4`
  - ZIP: `application/zip`

**Note**: Artifact types use default MIME types (e.g., all ImageArtifacts become `image/png`). For precise MIME types, use the dict format with explicit `type` specification.

## Best Practices

1. **Always provide meaningful subject lines** - they improve email deliverability
2. **Include both text and HTML content** - ensures compatibility across all email clients
3. **Test with send=False first** - validate your email before sending
4. **Use artifact types when possible** - simplified handling with default MIME types and validation
5. **Respect size limits** - 10MB per file, 30MB total (enforced automatically)
6. **Verify sender email** - use a verified sender address in SendGrid
7. **Monitor the logs** - enable debug logs when troubleshooting
8. **Use URL artifacts efficiently** - VideoUrlArtifact and ImageUrlArtifact download automatically
9. **Mix attachment types** - combine artifacts and legacy dict format as needed
10. **Handle size violations gracefully** - check status parameter for size limit errors

## Troubleshooting

### "API key not found" error
- Ensure SENDGRID_API_KEY is set in configuration or environment
- Verify the API key has the correct permissions in SendGrid

### "Email not received" issues
- Check sender reputation and domain authentication
- Verify recipient email address
- Check spam/junk folders
- Review SendGrid delivery logs in the dashboard

### Size limit violations
- **Individual file too large**: Check status parameter for specific file sizes
- **Total email too large**: Reduce number or size of attachments
- **Size detection**: The node shows exact sizes in error messages
- **Prevention**: Use artifacts for automatic size validation

### Attachment issues
- **Artifact types**: Use supported artifact types for automatic handling
- **Legacy dict format**: Ensure files are properly base64 encoded
- **MIME types**: Artifact types use defaults, dict format allows manual specification or filename-based detection
- **URL downloads**: VideoUrlArtifact and ImageUrlArtifact download automatically
- **Mixed types**: Combine different artifact types in single email
- **Debug logs**: Enable to see detailed attachment processing information
