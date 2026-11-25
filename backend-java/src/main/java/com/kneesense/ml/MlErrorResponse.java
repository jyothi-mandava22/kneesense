package com.kneesense.ml;

/** Error envelope returned by the Python ML service. */
public record MlErrorResponse(String error, String message) {
}
