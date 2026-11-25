package com.kneesense.api.admin;

public class InvalidAdminOperationException extends RuntimeException {
    public InvalidAdminOperationException(String message) {
        super(message);
    }
}
