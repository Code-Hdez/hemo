class ChatResourceNotFound(LookupError):
    """A requested conversation or analysis is absent or not owned by the user."""


class ChatRuntimeUnavailable(RuntimeError):
    """An external chat dependency is unavailable."""

    def __init__(
        self,
        code: str = "provider_unavailable",
        *,
        conversation_id: str | None = None,
        attempt: int | None = None,
    ) -> None:
        super().__init__(code)
        self.code = code
        self.conversation_id = conversation_id
        self.attempt = attempt

    def bind_turn(self, conversation_id: str, attempt: int) -> "ChatRuntimeUnavailable":
        self.conversation_id = conversation_id
        self.attempt = attempt
        return self


class ChatTurnInProgress(RuntimeError):
    """The same idempotent client turn is already being processed."""

    def __init__(
        self,
        *,
        conversation_id: str | None = None,
        attempt: int | None = None,
    ) -> None:
        super().__init__("turn_in_progress")
        self.conversation_id = conversation_id
        self.attempt = attempt


class ChatIdempotencyConflict(RuntimeError):
    """A client message id was reused with different immutable request data."""

    def __init__(
        self,
        *,
        conversation_id: str | None = None,
        attempt: int | None = None,
    ) -> None:
        super().__init__("idempotency_conflict")
        self.conversation_id = conversation_id
        self.attempt = attempt


class ChatPersistenceError(RuntimeError):
    """A turn could not be persisted consistently."""


class ChatTurnConcurrencyConflict(ChatPersistenceError):
    """The expected turn attempt/state lost its compare-and-set race."""

    def __init__(
        self,
        *,
        conversation_id: str | None = None,
        attempt: int | None = None,
        reason: str = "turn_completion_conflict",
    ) -> None:
        super().__init__(reason)
        self.code = "turn_completion_conflict"
        self.conversation_id = conversation_id
        self.attempt = attempt
        self.reason = reason


class ChatContextRevisionConflict(RuntimeError):
    """The client submitted a message for an obsolete context revision."""

    def __init__(
        self,
        *,
        conversation_id: str | None = None,
        attempt: int | None = None,
    ) -> None:
        super().__init__("context_revision_conflict")
        self.conversation_id = conversation_id
        self.attempt = attempt
