package com.kneesense.api.assessment.exception;

public class AssessmentUserUnavailableException extends RuntimeException {

    public AssessmentUserUnavailableException() {
        super("Authentication required.");
    }
}
