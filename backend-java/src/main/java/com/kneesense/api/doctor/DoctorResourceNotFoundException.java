package com.kneesense.api.doctor;

public class DoctorResourceNotFoundException extends RuntimeException {

    public DoctorResourceNotFoundException(String message) {
        super(message);
    }
}
