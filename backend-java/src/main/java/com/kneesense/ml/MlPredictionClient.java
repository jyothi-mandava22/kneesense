package com.kneesense.ml;

import org.springframework.http.MediaType;

/** Calls the Python prediction service without exposing its credentials to the browser. */
public interface MlPredictionClient {

    MlPredictionResponse predict(byte[] imageBytes, MediaType mediaType, String filename);

    /**
     * Requests prediction with optional cached-report-only mode.
     * Existing implementations remain compatible through this default method.
     */
    default MlPredictionResponse predict(
        byte[] imageBytes,
        MediaType mediaType,
        String filename,
        boolean forceCachedReports
    ) {
        return predict(imageBytes, mediaType, filename);
    }
}
