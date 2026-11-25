package com.kneesense.ml;

import com.fasterxml.jackson.databind.ObjectMapper;
import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.assertEquals;

class MlPredictionResponseContractTest {

    private static final String PNG_BASE64 =
        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+jx9sAAAAASUVORK5CYII=";

    @Test
    void mapsExactSnakeCaseMlContractFields() throws Exception {
        String json = """
            {
              "kl_grade": 2,
              "confidence": 0.51,
              "heatmap_base64": "%s",
              "clinician_report": "clinician text",
              "patient_report": "patient text",
              "source": "cached"
            }
            """.formatted(PNG_BASE64);

        MlPredictionResponse response = new ObjectMapper().readValue(json, MlPredictionResponse.class);

        assertEquals(2, response.klGrade());
        assertEquals("0.51", response.confidence().toPlainString());
        assertEquals("clinician text", response.clinicianReport());
        assertEquals("patient text", response.patientReport());
        assertEquals("cached", response.source());
    }
}
