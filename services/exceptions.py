"""Ошибки бизнес-логики. Слой бота превращает их в понятные пользователю сообщения."""


class ServiceError(Exception):
    pass


class DialogNotFoundError(ServiceError):
    def __init__(self, dialog_id: str) -> None:
        super().__init__(f"Dialog {dialog_id!r} not found")
        self.dialog_id = dialog_id


class DialogLimitError(ServiceError):
    def __init__(self, limit: int) -> None:
        super().__init__(f"Dialog limit {limit} reached")
        self.limit = limit


class InvalidDialogTitleError(ServiceError):
    def __init__(self, max_length: int) -> None:
        super().__init__("Invalid dialog title")
        self.max_length = max_length


class UnknownModeError(ServiceError):
    def __init__(self, mode_id: str) -> None:
        super().__init__(f"Unknown mode {mode_id!r}")
        self.mode_id = mode_id


class EmptyMessageError(ServiceError):
    pass


class MessageTooLongError(ServiceError):
    def __init__(self, length: int, limit: int) -> None:
        super().__init__(f"Message too long: {length} > {limit}")
        self.length = length
        self.limit = limit


class UserBusyError(ServiceError):
    """Пользователь отправил новое сообщение, пока модель отвечает на предыдущее."""
