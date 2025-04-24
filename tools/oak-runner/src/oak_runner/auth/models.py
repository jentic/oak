#!/usr/bin/env python3
"""
Authentication Models for OAK Runner.

This module defines Pydantic models for different authentication schemas used in
OpenAPI specifications and Arazzo workflows.
"""

from enum import Enum, auto
from typing import Dict, List, Optional, Union, Any
from pydantic import BaseModel, Field, HttpUrl, ConfigDict

# Environment variable key constants
class EnvVarKeys:
    """Constants for environment variable keys used in authentication."""
    API_KEY = 'apiKey'
    TOKEN = 'token'
    USERNAME = 'username'
    PASSWORD = 'password'
    AUTH_VALUE = 'auth_value'
    CLIENT_ID = 'client_id'
    CLIENT_SECRET = 'client_secret'
    REDIRECT_URI = 'redirect_uri'


# Authentication Types
class AuthLocation(str, Enum):
    """Locations where authentication credentials can be provided."""
    HEADER = "header"
    QUERY = "query"
    COOKIE = "cookie"
    PATH = "path"
    BODY = "body"


class AuthType(str, Enum):
    """Types of authentication schemas supported."""
    API_KEY = "apiKey"
    HTTP = "http"
    OAUTH2 = "oauth2"
    OPENID = "openIdConnect"
    CUSTOM = "custom"


class HttpSchemeType(str, Enum):
    """HTTP authentication scheme types."""
    BASIC = "basic"
    BEARER = "bearer"
    DIGEST = "digest"
    MUTUAL = "mutual"
    NEGOTIATE = "negotiate"
    OAUTH = "oauth"
    SCRAM_SHA_1 = "scram-sha-1"
    SCRAM_SHA_256 = "scram-sha-256"
    VAPID = "vapid"
    CUSTOM = "custom"


class OAuth2FlowType(str, Enum):
    """OAuth2 flow types."""
    AUTHORIZATION_CODE = "authorizationCode"
    IMPLICIT = "implicit"
    PASSWORD = "password"
    CLIENT_CREDENTIALS = "clientCredentials"


# Base Security Scheme
class SecurityScheme(BaseModel):
    """Base model for all authentication schemas."""
    type: AuthType
    name: str
    description: Optional[str] = None


# API Key Authentication
class ApiKeyScheme(SecurityScheme):
    """API Key authentication schema."""
    type: AuthType = AuthType.API_KEY
    location: AuthLocation
    parameter_name: str = Field(..., description="Name of the parameter to use for the API key")


# HTTP Authentication
class HttpAuthScheme(SecurityScheme):
    """HTTP authentication schema (Basic, Bearer, etc.)."""
    type: AuthType = AuthType.HTTP
    scheme: HttpSchemeType
    location: AuthLocation = AuthLocation.HEADER
    bearer_format: Optional[str] = None  # For Bearer auth, e.g., 'JWT'


# OAuth2 URLs
class OAuth2Urls(BaseModel):
    """URLs used in OAuth2 flows."""
    authorization: Optional[HttpUrl] = None
    token: Optional[HttpUrl] = None
    refresh: Optional[HttpUrl] = None


# OAuth2 Flow
class OAuth2Flow(BaseModel):
    """Represents an OAuth2 flow configuration."""
    scopes: Dict[str, str] = Field(default_factory=dict, description="Available scopes and their descriptions")
    
    model_config = ConfigDict(extra="forbid")


# OAuth2 Authorization Code Flow
class AuthorizationCodeFlow(OAuth2Flow):
    """Authorization Code flow for OAuth2."""
    authorization_url: HttpUrl
    token_url: HttpUrl
    refresh_url: Optional[HttpUrl] = None


# OAuth2 Implicit Flow
class ImplicitFlow(OAuth2Flow):
    """Implicit flow for OAuth2."""
    authorization_url: HttpUrl


# OAuth2 Password Flow
class PasswordFlow(OAuth2Flow):
    """Password flow for OAuth2."""
    token_url: HttpUrl


# OAuth2 Client Credentials Flow
class ClientCredentialsFlow(OAuth2Flow):
    """Client Credentials flow for OAuth2."""
    token_url: HttpUrl


# OAuth2 Flows Container
class OAuth2Flows(BaseModel):
    """Container for all OAuth2 flows defined in a security scheme."""
    authorization_code: Optional[AuthorizationCodeFlow] = None
    implicit: Optional[ImplicitFlow] = None
    password: Optional[PasswordFlow] = None
    client_credentials: Optional[ClientCredentialsFlow] = None
    
    model_config = ConfigDict(extra="forbid")


# OAuth2 Authentication
class OAuth2Scheme(SecurityScheme):
    """OAuth2 authentication schema."""
    type: AuthType = AuthType.OAUTH2
    flows: OAuth2Flows = Field(default_factory=OAuth2Flows)


# OpenID Connect Authentication
class OpenIDScheme(SecurityScheme):
    """OpenID Connect authentication schema."""
    type: AuthType = AuthType.OPENID
    openid_connect_url: HttpUrl


# Custom Authentication
class CustomScheme(SecurityScheme):
    """Custom authentication schema for non-standard auth methods."""
    type: AuthType = AuthType.CUSTOM
    parameters: Dict[str, str] = Field(default_factory=dict)


# Union type for all authentication schemas
SecuritySchemeUnion = Union[ApiKeyScheme, HttpAuthScheme, OAuth2Scheme, OpenIDScheme, CustomScheme]


class RequestAuthValue(BaseModel):
    """
    Represents an authentication value to be applied to an HTTP request.
    
    This model defines where and how an authentication value should be applied
    to an outgoing HTTP request.
    """
    location: AuthLocation
    name: str
    auth_value: str
    
    model_config = ConfigDict(extra="forbid")


# Base Auth class for all authentication values
class BaseAuth(BaseModel):
    """Base class for all authentication values."""
    type: AuthType
    
    model_config = ConfigDict(extra="forbid")


# Authentication Value Types
class BasicAuth(BaseAuth):
    """Credentials for HTTP Basic authentication."""
    type: AuthType = AuthType.HTTP
    username: str
    password: str
    
    model_config = ConfigDict(extra="forbid")


class BearerAuth(BaseAuth):
    """Token for HTTP Bearer authentication."""
    type: AuthType = AuthType.HTTP
    token: str
    
    model_config = ConfigDict(extra="forbid")


class ApiKeyAuth(BaseAuth):
    """API Key authentication value."""
    type: AuthType = AuthType.API_KEY
    api_key: str
    
    model_config = ConfigDict(extra="forbid")


class OAuth2Web(BaseAuth):
    """OAuth2 authentication values."""
    type: AuthType = AuthType.OAUTH2
    flow_type: OAuth2FlowType
    access_token: str
    token_type: str = "Bearer"
    refresh_token: Optional[str] = None
    expires_in: Optional[int] = None
    scope: Optional[str] = None
    
    model_config = ConfigDict(extra="forbid")


class OAuth2ClientCredentials(BaseAuth):
    """OAuth2 client credentials."""
    type: AuthType = AuthType.OAUTH2
    flow_type: OAuth2FlowType = OAuth2FlowType.CLIENT_CREDENTIALS
    client_id: str
    client_secret: str
    access_token: str
    
    model_config = ConfigDict(extra="forbid")


class OAuth2AccessTokenOnly(BaseAuth):
    """OAuth2 access token only."""
    type: AuthType = AuthType.OAUTH2
    access_token: str
    token_type: str = "Bearer"
    refresh_token: Optional[str] = None
    expires_in: Optional[int] = None
    scope: Optional[str] = None
    
    model_config = ConfigDict(extra="forbid")


class OpenIDAuth(BaseAuth):
    """OpenID Connect authentication value."""
    type: AuthType = AuthType.OPENID
    access_token: str
    token_type: str = "Bearer"
    refresh_token: Optional[str] = None
    expires_in: Optional[int] = None
    scope: Optional[str] = None
    
    model_config = ConfigDict(extra="forbid")


# Union type for all authentication values
AuthValue = Union[BasicAuth, BearerAuth, ApiKeyAuth, OAuth2Web, OAuth2ClientCredentials, OpenIDAuth, OAuth2AccessTokenOnly]


# Security Requirements
class SecurityRequirement(BaseModel):
    """
    Represents a single security requirement in OpenAPI.
    
    In OpenAPI, security requirements are objects where:
    - Each key is a security scheme name
    - Each value is an array of scopes required for that scheme
    
    Example:
    {
      "api_key": [],
      "oauth2": ["read:pets", "write:pets"]
    }
    """
    scheme_name: str
    scopes: List[str] = Field(default_factory=list)
    
    model_config = ConfigDict(extra="forbid")


class SecurityOption(BaseModel):
    """
    Represents a single security option in OpenAPI.
    
    In OpenAPI security, each object in the security array represents an alternative
    option (OR relationship). Within each option, multiple schemes can be specified,
    which must all be satisfied (AND relationship).
    
    Example of a security array with multiple options:
    [
      {"api_key": []},                         # Option 1: Use API key only
      {"oauth2": ["read:pets", "write:pets"]}  # Option 2: Use OAuth2 with these scopes
    ]
    """
    requirements: List[SecurityRequirement] = Field(default_factory=list)
    
    model_config = ConfigDict(extra="forbid")


# Conversion functions
def auth_requirement_to_schema(req: 'AuthRequirement') -> SecuritySchemeUnion:
    """
    Convert an AuthRequirement object to the appropriate Pydantic schema.
    
    Args:
        req: The AuthRequirement object to convert
        
    Returns:
        The corresponding Pydantic schema object
    """
    # Common attributes
    common = {
        "name": req.name,
        "description": req.description,
        "required": req.required
    }
    
    if req.auth_type == AuthType.API_KEY:
        location = AuthLocation.HEADER
        if req.location:
            try:
                location = AuthLocation(req.location.value)
            except ValueError:
                pass
            
        return ApiKeyScheme(
            **common,
            location=location,
            parameter_name=req.name
        )
        
    elif req.auth_type == AuthType.HTTP:
        scheme = HttpSchemeType.CUSTOM
        if req.schemes and len(req.schemes) > 0:
            try:
                scheme = HttpSchemeType(req.schemes[0].lower())
            except ValueError:
                pass
                
        return HttpAuthScheme(
            **common,
            scheme=scheme
        )
        
    elif req.auth_type == AuthType.OAUTH2:
        flow_type = OAuth2FlowType.AUTHORIZATION_CODE
        if req.flow_type:
            try:
                flow_type = OAuth2FlowType(req.flow_type)
            except ValueError:
                pass
                
        auth_urls = OAuth2Urls()
        if req.auth_urls:
            auth_urls = OAuth2Urls(
                authorization=req.auth_urls.get("authorization"),
                token=req.auth_urls.get("token"),
                refresh=req.auth_urls.get("refresh")
            )
            
        flows = OAuth2Flows()
        if flow_type == OAuth2FlowType.AUTHORIZATION_CODE:
            flows.authorization_code = AuthorizationCodeFlow(
                authorization_url=auth_urls.authorization,
                token_url=auth_urls.token,
                refresh_url=auth_urls.refresh
            )
        elif flow_type == OAuth2FlowType.IMPLICIT:
            flows.implicit = ImplicitFlow(
                authorization_url=auth_urls.authorization
            )
        elif flow_type == OAuth2FlowType.PASSWORD:
            flows.password = PasswordFlow(
                token_url=auth_urls.token
            )
        elif flow_type == OAuth2FlowType.CLIENT_CREDENTIALS:
            flows.client_credentials = ClientCredentialsFlow(
                token_url=auth_urls.token
            )
            
        return OAuth2Scheme(
            **common,
            flows=flows
        )
        
    elif req.auth_type == AuthType.OPENID:
        openid_url = None
        if req.auth_urls and "openid_configuration" in req.auth_urls:
            openid_url = req.auth_urls["openid_configuration"]
            
        return OpenIDScheme(
            **common,
            openid_connect_url=openid_url or "https://example.com/.well-known/openid-configuration"
        )
        
    else:  # CUSTOM or unknown
        return CustomScheme(**common)
