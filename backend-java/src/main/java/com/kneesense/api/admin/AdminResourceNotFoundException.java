package com.kneesense.api.admin;

public class AdminResourceNotFoundException extends RuntimeException {
    public AdminResourceNotFoundException(String message) {
        super(message);
    }
}
