"""
SendGrid Email Node
Sends emails using the SendGrid API with support for text, HTML content and attachments.
"""
from typing import Any
import base64
import mimetypes

from griptape_nodes.exe_types.core_types import (
    Parameter,
    ParameterMode,
    ParameterTypeBuiltin,
    ParameterList
)
from griptape.artifacts import (
    UrlArtifact,
    TextArtifact,
    ImageArtifact,
    ImageUrlArtifact,
    AudioArtifact
)

from griptape_nodes.exe_types.node_types import DataNode, NodeResolutionState, BaseNode
from griptape_nodes.retained_mode.griptape_nodes import GriptapeNodes

try:
    import sendgrid
    from sendgrid.helpers.mail import Mail, Email, To, Content, Attachment, FileContent, FileName, FileType, Disposition
    SENDGRID_AVAILABLE = True
except ImportError:
    SENDGRID_AVAILABLE = False

# Optional dependency for downloading ImageUrlArtifacts
try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False


class VideoArtifact:
    """
    Artifact that contains binary video data.
    """
    def __init__(self, value: bytes, name: str | None = None):
        self.value = value
        self.name = name or self.__class__.__name__
        self.mime_type = "video/mp4"
        self.media_type = "video"


class VideoUrlArtifact(UrlArtifact):
    """
    Artifact that contains a URL to a video.
    """
    def __init__(self, url: str, name: str | None = None):
        super().__init__(value=url, name=name or self.__class__.__name__)
        self.mime_type = "video/mp4"
        self.media_type = "video"


class SendGridEmailNode(DataNode):
    """A node for sending emails using SendGrid API."""
    
    def __init__(self, name: str, metadata: dict[Any, Any] | None = None) -> None:
        super().__init__(name, metadata)
        
        self.category = "Communication"
        self.description = "Send emails using SendGrid with text, HTML content and attachments"
        
        # To email parameter
        self.add_parameter(
            Parameter(
                name="to",
                tooltip="Email address to send to",
                type=ParameterTypeBuiltin.STR.value,
                allowed_modes={ParameterMode.INPUT, ParameterMode.PROPERTY},
                ui_options={
                    "display_name": "To Email",
                    "placeholder_text": "recipient@example.com"
                }
            )
        )
        
        # From email parameter
        self.add_parameter(
            Parameter(
                name="from",
                tooltip="Email address the message is from",
                type=ParameterTypeBuiltin.STR.value,
                allowed_modes={ParameterMode.INPUT, ParameterMode.PROPERTY},
                ui_options={
                    "display_name": "From Email",
                    "placeholder_text": "sender@example.com"
                }
            )
        )
        
        # Subject parameter
        self.add_parameter(
            Parameter(
                name="subject",
                tooltip="Email subject line",
                type=ParameterTypeBuiltin.STR.value,
                allowed_modes={ParameterMode.INPUT, ParameterMode.PROPERTY},
                default_value="",
                ui_options={
                    "display_name": "Subject",
                    "placeholder_text": "Email subject"
                }
            )
        )
        
        # Text content parameter
        self.add_parameter(
            Parameter(
                name="text_content",
                tooltip="The body of the email in plain text format",
                type=ParameterTypeBuiltin.STR.value,
                allowed_modes={ParameterMode.INPUT, ParameterMode.PROPERTY},
                default_value="",
                ui_options={
                    "display_name": "Text Content",
                    "multiline": True,
                    "is_full_width": True,
                    "placeholder_text": "Plain text email content..."
                }
            )
        )
        
        # HTML content parameter
        self.add_parameter(
            Parameter(
                name="html_content",
                tooltip="The body of the email in HTML format",
                type=ParameterTypeBuiltin.STR.value,
                allowed_modes={ParameterMode.INPUT, ParameterMode.PROPERTY},
                default_value="",
                ui_options={
                    "display_name": "HTML Content",
                    "multiline": True,
                    "is_full_width": True,
                    "placeholder_text": "<html><body><h1>HTML email content...</h1></body></html>"
                }
            )
        )
        
        # Attachments parameter (accepts various artifact types)
        self.add_parameter(
            ParameterList(
                name="attachments",
                tooltip="List of attachments - supports TextArtifact, ImageArtifact, ImageUrlArtifact, AudioArtifact, VideoArtifact, VideoUrlArtifact, or legacy dict format",
                input_types=["TextArtifact", "ImageArtifact", "ImageUrlArtifact", "AudioArtifact", "VideoArtifact", "VideoUrlArtifact", "dict"],
                allowed_modes={ParameterMode.INPUT, ParameterMode.PROPERTY},
                ui_options={
                    "display_name": "Attachments"
                }
            )
        )
        
        # Send toggle parameter
        self.add_parameter(
            Parameter(
                name="send",
                tooltip="Enable/disable sending the email. When disabled, the node will not send the email",
                type=ParameterTypeBuiltin.BOOL.value,
                allowed_modes={ParameterMode.INPUT, ParameterMode.PROPERTY},
                default_value=True,
                ui_options={
                    "display_name": "Send Email"
                }
            )
        )
        
        # Output status parameter
        self.add_parameter(
            Parameter(
                name="status",
                tooltip="Email sending status and response",
                type=ParameterTypeBuiltin.STR.value,
                allowed_modes={ParameterMode.OUTPUT},
                ui_options={
                    "display_name": "Status",
                    "multiline": True
                }
            )
        )
        
        # Debug logs parameter
        self.add_parameter(
            Parameter(
                name="logs",
                tooltip="Detailed logs for debugging email sending process",
                type=ParameterTypeBuiltin.STR.value,
                allowed_modes={ParameterMode.OUTPUT},
                default_value="",
                ui_options={
                    "display_name": "Debug Logs",
                    "multiline": True,
                    "hide": True
                }
            )
        )

    def _check_attachment_size(self, content: str, filename: str, logs: list) -> None:
        """
        Check if attachment size is within limits.
        Raises ValueError if size exceeds limits.
        """
        # Calculate size of base64 content (this is larger than original due to encoding)
        # Base64 encoding increases size by ~33%, so we check the decoded size
        content_bytes = len(content.encode('utf-8'))
        # Approximate original file size (base64 is ~33% larger)
        original_size_mb = (content_bytes * 0.75) / (1024 * 1024)
        
        logs.append(f"DEBUG: Attachment '{filename}' size: {original_size_mb:.2f} MB")
        
        if original_size_mb > 10:
            error_msg = f"Attachment '{filename}' ({original_size_mb:.2f} MB) exceeds 10MB limit. Email processing aborted."
            logs.append(f"ERROR: {error_msg}")
            raise ValueError(error_msg)

    def _get_mime_type(self, artifact: Any, filename: str = None) -> str:
        """Determine MIME type from artifact type and filename."""
        if isinstance(artifact, ImageArtifact) or isinstance(artifact, ImageUrlArtifact):
            return "image/png"  # Default for images, could be enhanced
        elif isinstance(artifact, AudioArtifact):
            return "audio/mpeg"  # Default for audio
        elif isinstance(artifact, VideoUrlArtifact) or (hasattr(artifact, '__class__') and 'VideoUrl' in artifact.__class__.__name__):
            return "video/mp4"  # Default for video
        elif isinstance(artifact, VideoArtifact) or (hasattr(artifact, '__class__') and 'VideoArtifact' == artifact.__class__.__name__):
            return "video/mp4"  # Default for video
        elif isinstance(artifact, TextArtifact):
            return "text/plain"
        else:
            # For dict or other types, use filename-based detection
            if filename:
                mime_type, _ = mimetypes.guess_type(filename)
                if mime_type:
                    return mime_type
            return "application/octet-stream"

    def _extract_attachment_data(self, artifact: Any, index: int, logs: list = None) -> tuple[str, str, str] | None:
        """Extract filename, base64 content, and mime type from an artifact.
        
        Returns: (filename, base64_content, mime_type) or None if processing fails
        """
        if logs is None:
            logs = []
            
        try:
            logs.append(f"DEBUG: _extract_attachment_data called with artifact type: {type(artifact).__name__}")
            logs.append(f"DEBUG: Artifact details: {str(artifact)[:100]}")
            
            if hasattr(artifact, 'value'):
                logs.append(f"DEBUG: Artifact has value attribute, type: {type(artifact.value)}")
            
            if hasattr(artifact, 'name'):
                logs.append(f"DEBUG: Artifact has name attribute: {artifact.name}")
            else:
                logs.append("DEBUG: Artifact does not have name attribute")
            if isinstance(artifact, dict):
                # Legacy dict format support
                logs.append("DEBUG: Processing dict artifact")
                filename = artifact.get('filename', f'attachment_{index}')
                content = artifact.get('content', '')
                file_type = artifact.get('type', 'application/octet-stream')
                
                # Check attachment size for dict format (content may not be base64 encoded)
                content_size_mb = len(content.encode('utf-8')) / (1024 * 1024)
                logs.append(f"DEBUG: Dict attachment '{filename}' size: {content_size_mb:.2f} MB")
                if content_size_mb > 10:
                    error_msg = f"Attachment '{filename}' ({content_size_mb:.2f} MB) exceeds 10MB limit. Email processing aborted."
                    logs.append(f"ERROR: {error_msg}")
                    raise ValueError(error_msg)
                    
                logs.append(f"DEBUG: Dict artifact - filename: {filename}, content_length: {len(content)}, type: {file_type}")
                return filename, content, file_type
            
            elif isinstance(artifact, TextArtifact):
                logs.append("DEBUG: Processing TextArtifact")
                filename = getattr(artifact, 'name', f'text_attachment_{index}.txt')
                content = base64.b64encode(artifact.value.encode('utf-8')).decode('utf-8')
                mime_type = self._get_mime_type(artifact, filename)
                
                # Check attachment size
                self._check_attachment_size(content, filename, logs)
                    
                logs.append(f"DEBUG: TextArtifact - filename: {filename}, content_length: {len(content)}, mime_type: {mime_type}")
                return filename, content, mime_type
            
            elif isinstance(artifact, VideoArtifact) or (hasattr(artifact, '__class__') and 'VideoArtifact' == artifact.__class__.__name__):
                logs.append("DEBUG: Processing VideoArtifact")
                filename = getattr(artifact, 'name', f'video_{index}.mp4')
                content = base64.b64encode(artifact.value).decode('utf-8')
                mime_type = self._get_mime_type(artifact, filename)
                
                # Check attachment size
                self._check_attachment_size(content, filename, logs)
                    
                logs.append(f"DEBUG: VideoArtifact - filename: {filename}, content_length: {len(content)}, mime_type: {mime_type}")
                return filename, content, mime_type
            
            elif isinstance(artifact, ImageArtifact):
                logs.append("DEBUG: Processing ImageArtifact")
                filename = getattr(artifact, 'name', f'image_{index}.png')
                content = base64.b64encode(artifact.value).decode('utf-8')
                mime_type = self._get_mime_type(artifact, filename)
                
                # Check attachment size
                self._check_attachment_size(content, filename, logs)
                    
                logs.append(f"DEBUG: ImageArtifact - filename: {filename}, content_length: {len(content)}, mime_type: {mime_type}")
                return filename, content, mime_type
            
            elif isinstance(artifact, ImageUrlArtifact):
                # For URL artifacts, we need to download the content
                logs.append("DEBUG: Processing ImageUrlArtifact")
                filename = getattr(artifact, 'name', f'image_{index}.png')
                logs.append(f"DEBUG: ImageUrlArtifact URL: {artifact.value}")
                if not REQUESTS_AVAILABLE:
                    logs.append("DEBUG: Requests not available, skipping ImageUrlArtifact")
                    # Skip URL artifacts if requests is not available
                    return None
                try:
                    logs.append(f"DEBUG: Downloading from URL: {artifact.value}")
                    response = requests.get(artifact.value, timeout=30)
                    response.raise_for_status()
                    content = base64.b64encode(response.content).decode('utf-8')
                    mime_type = self._get_mime_type(artifact, filename)
                    
                    # Check attachment size
                    self._check_attachment_size(content, filename, logs)
                        
                    logs.append(f"DEBUG: ImageUrlArtifact - filename: {filename}, content_length: {len(content)}, mime_type: {mime_type}")
                    return filename, content, mime_type
                except ValueError as size_error:
                    # Size violation - let it propagate up to abort email processing
                    raise size_error
                except Exception as e:
                    logs.append(f"DEBUG: Failed to download ImageUrlArtifact: {str(e)}")
                    # If download fails, skip this attachment
                    return None
            
            elif isinstance(artifact, AudioArtifact):
                logs.append("DEBUG: Processing AudioArtifact")
                filename = getattr(artifact, 'name', f'audio_{index}.mp3')
                content = base64.b64encode(artifact.value).decode('utf-8')
                mime_type = self._get_mime_type(artifact, filename)
                
                # Check attachment size
                self._check_attachment_size(content, filename, logs)
                    
                logs.append(f"DEBUG: AudioArtifact - filename: {filename}, content_length: {len(content)}, mime_type: {mime_type}")
                return filename, content, mime_type
            
            elif isinstance(artifact, VideoUrlArtifact) or (hasattr(artifact, '__class__') and 'VideoUrl' in artifact.__class__.__name__):
                # For video URL artifacts, we need to download the content
                logs.append("DEBUG: Processing VideoUrlArtifact")
                filename = getattr(artifact, 'name', f'video_{index}.mp4')
                logs.append(f"DEBUG: VideoUrlArtifact URL: {artifact.value}")
                if not REQUESTS_AVAILABLE:
                    logs.append("DEBUG: Requests not available, skipping VideoUrlArtifact")
                    # Skip URL artifacts if requests is not available
                    return None
                try:
                    logs.append(f"DEBUG: Downloading video from URL: {artifact.value}")
                    response = requests.get(artifact.value, timeout=60)  # Longer timeout for video files
                    response.raise_for_status()
                    content = base64.b64encode(response.content).decode('utf-8')
                    mime_type = self._get_mime_type(artifact, filename)
                    
                    # Check attachment size
                    self._check_attachment_size(content, filename, logs)
                        
                    logs.append(f"DEBUG: VideoUrlArtifact - filename: {filename}, content_length: {len(content)}, mime_type: {mime_type}")
                    return filename, content, mime_type
                except ValueError as size_error:
                    # Size violation - let it propagate up to abort email processing
                    raise size_error
                except Exception as e:
                    logs.append(f"DEBUG: Failed to download VideoUrlArtifact: {str(e)}")
                    # If download fails, skip this attachment
                    return None
            
            else:
                # Unknown artifact type
                logs.append(f"DEBUG: Unknown artifact type: {type(artifact).__name__}")
                return None
                
        except ValueError as size_error:
            # Size violation - let it propagate up to abort email processing
            raise size_error
        except Exception as e:
            logs.append(f"DEBUG: Exception in _extract_attachment_data: {str(e)}")
            import traceback
            logs.append(f"DEBUG: Traceback: {traceback.format_exc()}")
            return None

    def process(self) -> None:
        """Process the email and send it using SendGrid."""
        logs = []
        
        # Initialize logs output immediately
        self.parameter_output_values["logs"] = "Starting email processing...\n"
        
        # Log library availability
        logs.append(f"DEBUG: Requests available: {REQUESTS_AVAILABLE}")
        logs.append(f"DEBUG: SendGrid available: {SENDGRID_AVAILABLE}")
        
        # Check if sending is enabled
        send_enabled = self.get_parameter_value("send")
        logs.append(f"DEBUG: Send enabled: {send_enabled}")
        if not send_enabled:
            status_msg = "Email sending is disabled (send=False)"
            self.parameter_output_values["status"] = status_msg
            logs.append(status_msg)
            self.parameter_output_values["logs"] = "\n".join(logs)
            return
        
        # Check if SendGrid is available
        if not SENDGRID_AVAILABLE:
            error_msg = "SendGrid library not installed. Please install with: pip install sendgrid"
            self.parameter_output_values["status"] = error_msg
            logs.append(f"ERROR: {error_msg}")
            self.parameter_output_values["logs"] = "\n".join(logs)
            raise ImportError(error_msg)
        
        # Get parameter values
        to_email = self.get_parameter_value("to")
        from_email = self.get_parameter_value("from")
        subject = self.get_parameter_value("subject") or ""
        text_content = self.get_parameter_value("text_content") or ""
        html_content = self.get_parameter_value("html_content") or ""
        
        logs.append("DEBUG: Getting attachments parameter...")
        try:
            attachments = self.get_parameter_list_value("attachments") or []
            logs.append(f"DEBUG: Got attachments parameter successfully, count: {len(attachments)}")
        except Exception as e:
            logs.append(f"DEBUG: Error getting attachments parameter: {str(e)}")
            attachments = []
        
        logs.append(f"To: {to_email}")
        logs.append(f"From: {from_email}")
        logs.append(f"Subject: {subject}")
        logs.append(f"Text content length: {len(text_content)} chars")
        logs.append(f"HTML content length: {len(html_content)} chars")
        logs.append(f"Number of attachments: {len(attachments)}")
        logs.append(f"DEBUG: Attachment types: {[type(att).__name__ for att in attachments]}")
        logs.append(f"DEBUG: Raw attachments: {attachments}")
        
        # Update logs early so debugging info is visible
        self.parameter_output_values["logs"] = "\n".join(logs)
        
        # Validate required fields
        if not to_email:
            error_msg = "To email address is required"
            self.parameter_output_values["status"] = error_msg
            logs.append(f"ERROR: {error_msg}")
            self.parameter_output_values["logs"] = "\n".join(logs)
            raise ValueError(error_msg)
            
        if not from_email:
            error_msg = "From email address is required"
            self.parameter_output_values["status"] = error_msg
            logs.append(f"ERROR: {error_msg}")
            self.parameter_output_values["logs"] = "\n".join(logs)
            raise ValueError(error_msg)
            
        if not text_content and not html_content:
            error_msg = "Either text_content or html_content must be provided"
            self.parameter_output_values["status"] = error_msg
            logs.append(f"ERROR: {error_msg}")
            self.parameter_output_values["logs"] = "\n".join(logs)
            raise ValueError(error_msg)
        
        try:
            # Get API key from secrets manager
            api_key = GriptapeNodes.SecretsManager().get_secret("SENDGRID_API_KEY")
            if not api_key:
                error_msg = "SendGrid API key not found. Please set SENDGRID_API_KEY in configuration or environment variables"
                self.parameter_output_values["status"] = error_msg
                logs.append(f"ERROR: {error_msg}")
                self.parameter_output_values["logs"] = "\n".join(logs)
                raise ValueError(error_msg)
            
            logs.append("API key found")
            
            # Initialize SendGrid client
            sg = sendgrid.SendGridAPIClient(api_key=api_key)
            logs.append("SendGrid client initialized")
            
            # Create email components
            from_email_obj = Email(from_email)
            to_email_obj = To(to_email)
            
            # Create mail object - start with text content if available
            if text_content:
                content_obj = Content("text/plain", text_content)
                mail = Mail(from_email_obj, to_email_obj, subject, content_obj)
                logs.append("Created email with text content")
            else:
                # Create empty mail object
                mail = Mail()
                mail.from_email = from_email_obj
                mail.subject = subject
                # Add personalization
                personalization = mail.personalizations[0] if mail.personalizations else mail.add_personalization()
                personalization.add_to(to_email_obj)
            
            # Add HTML content if provided
            if html_content:
                html_content_obj = Content("text/html", html_content)
                mail.add_content(html_content_obj)
                logs.append("Added HTML content")
            
            # Process attachments
            if attachments:
                logs.append(f"Processing {len(attachments)} attachments")
                # Update logs before processing attachments
                self.parameter_output_values["logs"] = "\n".join(logs)
                
                # Track total email size
                total_email_size_mb = 0
                
                for i, attachment_artifact in enumerate(attachments):
                    try:
                        logs.append(f"DEBUG: Processing attachment {i}: {type(attachment_artifact).__name__}")
                        logs.append(f"DEBUG: Attachment {i} details: {str(attachment_artifact)[:200]}")
                        
                        # Update logs for each attachment
                        self.parameter_output_values["logs"] = "\n".join(logs)
                        
                        # Extract attachment data using utility function
                        attachment_data = self._extract_attachment_data(attachment_artifact, i, logs)
                    
                    except ValueError as size_error:
                        # Size limit exceeded - abort entire email processing
                        error_msg = str(size_error)
                        logs.append(f"ABORT: {error_msg}")
                        self.parameter_output_values["logs"] = "\n".join(logs)
                        # Re-raise the ValueError so it's caught by the main exception handler
                        raise size_error
                    
                    except Exception as e:
                        logs.append(f"ERROR: Failed to process attachment {i}: {str(e)}")
                        logs.append(f"WARNING: Skipping attachment {i} due to error")
                        continue
                    
                    # Continue processing the attachment data
                    logs.append(f"DEBUG: Attachment {i} extraction result: {attachment_data is not None}")
                    
                    if attachment_data is None:
                        logs.append(f"WARNING: Could not process attachment {i}, skipping")
                        continue
                    
                    filename, content, file_type = attachment_data
                    
                    logs.append(f"DEBUG: Attachment {i} - filename: {filename}, type: {file_type}, content_length: {len(content) if content else 0}")
                    
                    if not content:
                        logs.append(f"WARNING: Attachment {i} has no content, skipping")
                        continue
                    
                    # Track total email size (estimate based on content length)
                    attachment_size_mb = (len(content.encode('utf-8')) * 0.75) / (1024 * 1024)  # Account for base64 encoding
                    total_email_size_mb += attachment_size_mb
                    
                    logs.append(f"DEBUG: Total email size so far: {total_email_size_mb:.2f} MB")
                    
                    if total_email_size_mb > 30:
                        error_msg = f"Total email size ({total_email_size_mb:.2f} MB) exceeds 30MB limit. Aborting email processing."
                        logs.append(f"ERROR: {error_msg}")
                        self.parameter_output_values["logs"] = "\n".join(logs)
                        raise ValueError(error_msg)
                    
                    try:
                        # Create SendGrid attachment
                        attachment = Attachment()
                        attachment.file_content = FileContent(content)
                        attachment.file_name = FileName(filename)
                        attachment.file_type = FileType(file_type)
                        attachment.disposition = Disposition("attachment")
                        
                        logs.append(f"DEBUG: Created SendGrid attachment object for {filename}")
                        
                        mail.add_attachment(attachment)
                        logs.append(f"SUCCESS: Added attachment: {filename} ({file_type}) - {type(attachment_artifact).__name__}")
                        
                    except Exception as e:
                        logs.append(f"ERROR processing attachment {i}: {str(e)}")
                        import traceback
                        logs.append(f"DEBUG: Error traceback: {traceback.format_exc()}")
                        continue
            else:
                logs.append("DEBUG: No attachments to process")
            
            # Send the email
            logs.append("Sending email...")
            
            # Debug: Check final mail object
            mail_json = mail.get()
            logs.append(f"DEBUG: Final mail object attachments count: {len(mail_json.get('attachments', []))}")
            logs.append(f"DEBUG: Mail object keys: {list(mail_json.keys())}")
            
            response = sg.client.mail.send.post(request_body=mail_json)
            
            # Process response
            status_code = response.status_code
            response_body = response.body.decode('utf-8') if response.body else ""
            
            logs.append(f"Response status code: {status_code}")
            logs.append(f"Response body: {response_body}")
            
            if status_code == 202:
                status_msg = f"✅ Email sent successfully! Status code: {status_code}"
                logs.append("SUCCESS: Email sent successfully")
            else:
                status_msg = f"⚠️ Email sent with status code: {status_code}. Body: {response_body}"
                logs.append(f"WARNING: Unexpected status code: {status_code}")
            
            self.parameter_output_values["status"] = status_msg
            
        except Exception as e:
            # Check if this is a size violation error
            error_str = str(e)
            if "exceeds" in error_str and ("MB limit" in error_str or "10MB limit" in error_str or "30MB limit" in error_str):
                # This is a size violation - handle gracefully without raising exception
                error_msg = f"❌ {error_str}"
                self.parameter_output_values["status"] = error_msg
                logs.append(f"BLOCKED: {error_str}")
                # Don't raise exception - let node complete with error status
            else:
                # This is some other technical error - still raise exception
                error_msg = f"❌ Error sending email: {error_str}"
                self.parameter_output_values["status"] = error_msg
                logs.append(f"ERROR: {error_str}")
                raise Exception(f"Failed to send email: {error_str}")
        
        finally:
            # Always update logs
            self.parameter_output_values["logs"] = "\n".join(logs)

    def mark_for_processing(self) -> None:
        """Mark this node as needing to be processed."""
        self.state = NodeResolutionState.UNRESOLVED
        
        # Clear output values
        for param in self.parameters:
            if ParameterMode.OUTPUT in param.allowed_modes:
                self.parameter_output_values[param.name] = None

    def after_value_set(self, parameter: Parameter, value: Any) -> None:
        """Mark for reprocessing when relevant parameters change."""
        if parameter.name in ["to", "from", "subject", "text_content", "html_content", "attachments", "send"]:
            self.mark_for_processing()

    def after_incoming_connection(
        self,
        source_node: BaseNode,
        source_parameter: Parameter,
        target_parameter: Parameter,
    ) -> None:
        """Mark for processing when we get a new input connection."""
        if target_parameter.name in ["to", "from", "subject", "text_content", "html_content", "attachments", "send"]:
            self.mark_for_processing()

    def after_incoming_connection_removed(
        self,
        source_node: BaseNode,
        source_parameter: Parameter,
        target_parameter: Parameter,
    ) -> None:
        """Mark for processing when an input connection is removed."""
        if target_parameter.name in ["to", "from", "subject", "text_content", "html_content", "attachments", "send"]:
            self.mark_for_processing()
            self.remove_parameter_value(target_parameter.name)

    def validate_before_workflow_run(self) -> list[Exception] | None:
        """Validate the node configuration before running."""
        exceptions = []
        
        # Check if SendGrid is available
        if not SENDGRID_AVAILABLE:
            exceptions.append(ImportError("SendGrid library not installed. Please install with: pip install sendgrid"))
            return exceptions
            
        # Check for API key
        api_key = GriptapeNodes.SecretsManager().get_secret("SENDGRID_API_KEY")
        if not api_key:
            exceptions.append(ValueError("SENDGRID_API_KEY is not defined in configuration or environment variables"))
        
        return exceptions if exceptions else None
