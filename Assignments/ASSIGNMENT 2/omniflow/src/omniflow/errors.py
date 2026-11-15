class OmniFlowError(Exception):
    """Base class for domain errors."""

class Unauthenticated(OmniFlowError): pass
class Forbidden(OmniFlowError): pass
class NotFound(OmniFlowError): pass
class ValidationError(OmniFlowError): pass
class OutOfStock(OmniFlowError): pass
class InvalidTransition(OmniFlowError): pass
class VersionConflict(OmniFlowError): pass
class BadSignature(OmniFlowError): pass
class AmountMismatch(OmniFlowError): pass
class BufferFull(OmniFlowError): pass
class CourierError(OmniFlowError): pass
class GatewayError(OmniFlowError): pass
