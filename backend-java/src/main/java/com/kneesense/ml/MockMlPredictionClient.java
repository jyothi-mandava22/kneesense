package com.kneesense.ml;

import org.springframework.beans.factory.annotation.Value;
import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.http.MediaType;
import org.springframework.stereotype.Component;

/** Deterministic mock used for the first end-to-end vertical slice. */
@Component
@ConditionalOnProperty(name = "app.ml.mode", havingValue = "mock", matchIfMissing = true)
public class MockMlPredictionClient implements MlPredictionClient {

    private static final String MOCK_HEATMAP =
        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+jx9sAAAAASUVORK5CYII=";
    private static final String DISCLAIMER =
        "AI-generated summary — not a diagnosis, confirm with a doctor.";

    private final String errorCode;
    private final String source;

    public MockMlPredictionClient(
        @Value("${app.ml.mock.error-code:}") String errorCode,
        @Value("${app.ml.mock.source:cached}") String source
    ) {
        this.errorCode = errorCode;
        this.source = source;
    }

    @Override
    public MlPredictionResponse predict(byte[] imageBytes, MediaType mediaType, String filename) {
        if (errorCode != null && !errorCode.isBlank()) {
            throw MlServiceException.forCode(errorCode);
        }

        String patientReport = "MOCK RESULT — no model inference was performed. "
            + "The demonstration response is fixed at KL grade 2. " + DISCLAIMER;
        String clinicianReport = "MOCK CLINICIAN SUMMARY — no model inference was performed. "
            + "The demonstration response is fixed at KL grade 2. " + DISCLAIMER;

        return new MlPredictionResponse(
            2,
            new java.math.BigDecimal("0.510000"),
            MOCK_HEATMAP,
            clinicianReport,
            patientReport,
            source
        );
    }
}
