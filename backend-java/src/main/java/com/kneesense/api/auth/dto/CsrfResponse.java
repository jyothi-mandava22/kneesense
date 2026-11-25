package com.kneesense.api.auth.dto;

public record CsrfResponse(String headerName, String cookieName) {
}
