"""Main MediaSkill entry point."""
import uuid
from pathlib import Path
from typing import Optional

from .config import Config
from .session import SessionManager
from .router import ModelRouter


class MediaSkill:
    """Main entry point for media generation and understanding."""

    def __init__(self, config_path: str = "models.yaml", output_dir: Optional[str] = None):
        self.config = Config(config_path)
        self.session_manager = SessionManager()
        self.router = ModelRouter(self.config)
        self.output_dir = Path(output_dir or ".").resolve()

    async def generate_image(
        self,
        prompt: str,
        provider: Optional[str] = None,
        model: Optional[str] = None,
        session_id: Optional[str] = None,
        size: Optional[str] = None,
        quality: Optional[str] = None,
    ) -> dict:
        """Generate an image from a text prompt."""
        self.config.reload_if_changed()
        session = self.session_manager.get_or_create_session(session_id)
        params = {}
        if size:
            params["size"] = size
        if quality:
            params["quality"] = quality

        out_dir = self.output_dir / "generated" / session.session_id
        out_dir.mkdir(parents=True, exist_ok=True)
        output_path = str(out_dir / f"{uuid.uuid4().hex}.png")
        await self.router.generate_image(provider, model, prompt, params, output_path)
        ref = session.add_media_ref("image", output_path)
        session.add_message("user", prompt, {"type": "image", "ref": ref, "file_path": output_path})
        return {"file_path": output_path, "ref": ref}

    async def generate_video(
        self,
        prompt: str,
        provider: Optional[str] = None,
        model: Optional[str] = None,
        session_id: Optional[str] = None,
        duration: Optional[int] = None,
        resolution: Optional[str] = None,
    ) -> dict:
        """Generate a video from a text prompt."""
        self.config.reload_if_changed()
        session = self.session_manager.get_or_create_session(session_id)
        params = {}
        if duration:
            params["duration"] = duration
        if resolution:
            params["resolution"] = resolution

        out_dir = self.output_dir / "generated" / session.session_id
        out_dir.mkdir(parents=True, exist_ok=True)
        output_path = str(out_dir / f"{uuid.uuid4().hex}.mp4")
        await self.router.generate_video(provider, model, prompt, params, output_path)
        ref = session.add_media_ref("video", output_path)
        session.add_message("user", prompt, {"type": "video", "ref": ref, "file_path": output_path})
        return {"file_path": output_path, "ref": ref}

    async def understand_image(
        self,
        image: str,
        prompt: str = "Describe this image in detail.",
        provider: Optional[str] = None,
        model: Optional[str] = None,
        session_id: Optional[str] = None,
    ) -> dict:
        """Understand/analyze an image."""
        self.config.reload_if_changed()
        session = self.session_manager.get_or_create_session(session_id)
        result = await self.router.understand_image(provider, model, image, prompt, {})
        session.add_message("user", prompt, {"type": "image", "ref": None, "file_path": image})
        session.add_message("assistant", result)
        return {"description": result}

    async def understand_video(
        self,
        video: str,
        prompt: str = "Describe this video in detail.",
        provider: Optional[str] = None,
        model: Optional[str] = None,
        session_id: Optional[str] = None,
    ) -> dict:
        """Understand/analyze a video."""
        self.config.reload_if_changed()
        session = self.session_manager.get_or_create_session(session_id)
        result = await self.router.understand_video(provider, model, video, prompt, {})
        session.add_message("user", prompt, {"type": "video", "ref": None, "file_path": video})
        session.add_message("assistant", result)
        return {"description": result}

    async def edit_image(
        self,
        prompt: str,
        reference_image: Optional[str] = None,
        reference_ref: Optional[str] = None,
        provider: Optional[str] = None,
        model: Optional[str] = None,
        session_id: Optional[str] = None,
    ) -> dict:
        """Edit an image based on instructions."""
        self.config.reload_if_changed()
        session = self.session_manager.get_or_create_session(session_id)

        if reference_ref:
            resolved_path = session.get_media_ref(reference_ref)
            if not resolved_path:
                raise ValueError(f"Reference '{reference_ref}' not found in session")
            reference_image = resolved_path
        elif not reference_image:
            refs = session.get_recent_media_refs("image", 1)
            if refs:
                reference_image = session.get_media_ref(refs[0])
            else:
                raise ValueError("No reference image provided and no previous images in session")

        out_dir = self.output_dir / "generated" / session.session_id
        out_dir.mkdir(parents=True, exist_ok=True)
        output_path = str(out_dir / f"{uuid.uuid4().hex}_edited.png")
        await self.router.edit_image(provider, model, reference_image, prompt, {}, output_path)
        ref = session.add_media_ref("image", output_path)
        session.add_message("user", f"Edit: {prompt}", {"type": "image", "ref": ref, "file_path": output_path})
        return {"file_path": output_path, "ref": ref}

    async def edit_video(
        self,
        prompt: str,
        reference_video: Optional[str] = None,
        reference_ref: Optional[str] = None,
        provider: Optional[str] = None,
        model: Optional[str] = None,
        session_id: Optional[str] = None,
    ) -> dict:
        """Edit a video based on instructions."""
        self.config.reload_if_changed()
        session = self.session_manager.get_or_create_session(session_id)

        if reference_ref:
            resolved_path = session.get_media_ref(reference_ref)
            if not resolved_path:
                raise ValueError(f"Reference '{reference_ref}' not found in session")
            reference_video = resolved_path
        elif not reference_video:
            refs = session.get_recent_media_refs("video", 1)
            if refs:
                reference_video = session.get_media_ref(refs[0])
            else:
                raise ValueError("No reference video provided and no previous videos in session")

        out_dir = self.output_dir / "generated" / session.session_id
        out_dir.mkdir(parents=True, exist_ok=True)
        output_path = str(out_dir / f"{uuid.uuid4().hex}_edited.mp4")
        await self.router.edit_video(provider, model, reference_video, prompt, {}, output_path)
        ref = session.add_media_ref("video", output_path)
        session.add_message("user", f"Edit: {prompt}", {"type": "video", "ref": ref, "file_path": output_path})
        return {"file_path": output_path, "ref": ref}

    # Session management methods
    def list_sessions(self) -> list:
        return self.session_manager.list_sessions()

    def clear_session(self, session_id: str):
        self.session_manager.clear_session(session_id)

    def clear_default(self):
        self.session_manager.clear_default()

    def clear_expired(self, max_age_days: int = 7):
        self.session_manager.clear_expired(max_age_days)

    def get_history(self, session_id: Optional[str] = None) -> list:
        session = self.session_manager.get_or_create_session(session_id)
        return [msg.to_dict() for msg in session.get_history()]
