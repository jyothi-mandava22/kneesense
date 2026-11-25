package com.kneesense.api.assessment.exception;

public class AssessmentNotFoundException extends RuntimeException {

    public AssessmentNotFoundException() {
        super("Assessment not found.");
    }
}
