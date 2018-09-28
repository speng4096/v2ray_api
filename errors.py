class V2RayError(Exception):
    def __init__(self, details):
        self.details = details


class EmailExistsError(V2RayError):
    def __init__(self, details, email):
        self.email = email
        super(EmailExistsError, self).__init__(details)


class EmailNotFoundError(V2RayError):
    def __init__(self, details, email):
        self.email = email
        super(EmailNotFoundError, self).__init__(details)


class InboundNotFoundError(V2RayError):
    def __init__(self, details, inbound_tag):
        self.inbound_tag = inbound_tag
        super(InboundNotFoundError, self).__init__(details)


class AddressAlreadyInUseError(V2RayError):
    def __init__(self, details, port):
        self.port = port
        super(AddressAlreadyInUseError, self).__init__(details)
