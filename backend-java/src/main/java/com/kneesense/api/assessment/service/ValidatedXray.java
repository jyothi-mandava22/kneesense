package com.kneesense.api.assessment.service;

import org.springframework.http.MediaType;

public record ValidatedXray(byte[] bytes, MediaType mediaType, String filename, String sha256) {
}
