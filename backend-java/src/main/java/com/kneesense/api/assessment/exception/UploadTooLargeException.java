package com.kneesense.api.assessment.exception;

public class UploadTooLargeException extends RuntimeException {

    public UploadTooLargeException() {
        super("The image exceeds the 5 MiB upload limit.");
    }
}
