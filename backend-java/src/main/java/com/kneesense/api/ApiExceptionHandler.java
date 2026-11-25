package com.kneesense.api;

import com.kneesense.api.auth.EmailAlreadyRegisteredException;
import com.kneesense.api.auth.InvalidCredentialsException;
import com.kneesense.api.auth.PasswordTooLongException;
import com.kneesense.api.admin.AdminResourceNotFoundException;
import com.kneesense.api.admin.InvalidAdminOperationException;
import com.kneesense.api.doctor.DoctorResourceNotFoundException;
import com.kneesense.api.assessment.exception.AssessmentNotFoundException;
import com.kneesense.api.assessment.exception.AssessmentUserUnavailableException;
import com.kneesense.api.assessment.exception.InvalidXrayException;
import com.kneesense.api.assessment.exception.UploadTooLargeException;
import com.kneesense.ml.MlServiceException;
import org.springframework.dao.DataIntegrityViolationException;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.http.converter.HttpMessageNotReadableException;
import org.springframework.validation.FieldError;
import org.springframework.web.bind.MethodArgumentNotValidException;
import org.springframework.web.bind.MissingServletRequestParameterException;
import org.springframework.web.bind.annotation.ExceptionHandler;
import org.springframework.web.bind.annotation.RestControllerAdvice;
import org.springframework.web.multipart.MaxUploadSizeExceededException;

import java.util.Map;

@RestControllerAdvice
public class ApiExceptionHandler {

    @ExceptionHandler(EmailAlreadyRegisteredException.class)
    public ResponseEntity<Map<String, String>> emailExists(EmailAlreadyRegisteredException ex) {
        return error(HttpStatus.CONFLICT, "email_already_registered", ex.getMessage());
    }

    @ExceptionHandler(InvalidCredentialsException.class)
    public ResponseEntity<Map<String, String>> invalidCredentials(InvalidCredentialsException ex) {
        return error(HttpStatus.UNAUTHORIZED, "invalid_credentials", ex.getMessage());
    }

    @ExceptionHandler(PasswordTooLongException.class)
    public ResponseEntity<Map<String, String>> passwordTooLong(PasswordTooLongException ex) {
        return error(HttpStatus.BAD_REQUEST, "invalid_password", ex.getMessage());
    }

    @ExceptionHandler(MethodArgumentNotValidException.class)
    public ResponseEntity<Map<String, String>> invalidRequest(MethodArgumentNotValidException ex) {
        String message = ex.getBindingResult().getFieldErrors().stream()
            .findFirst()
            .map(FieldError::getDefaultMessage)
            .filter(value -> value != null && !value.isBlank())
            .orElse("Please check the submitted fields.");
        return error(HttpStatus.BAD_REQUEST, "invalid_request", message);
    }

    @ExceptionHandler(HttpMessageNotReadableException.class)
    public ResponseEntity<Map<String, String>> unreadableBody() {
        return error(HttpStatus.BAD_REQUEST, "invalid_request", "Request body is missing or invalid.");
    }

    @ExceptionHandler(MissingServletRequestParameterException.class)
    public ResponseEntity<Map<String, String>> missingRequestParameter() {
        return error(HttpStatus.BAD_REQUEST, "invalid_request", "A PNG or JPEG image file is required.");
    }

    @ExceptionHandler(AdminResourceNotFoundException.class)
    public ResponseEntity<Map<String, String>> adminResourceNotFound(AdminResourceNotFoundException ex) {
        return error(HttpStatus.NOT_FOUND, "not_found", ex.getMessage());
    }

    @ExceptionHandler(DoctorResourceNotFoundException.class)
    public ResponseEntity<Map<String, String>> doctorResourceNotFound(DoctorResourceNotFoundException ex) {
        return error(HttpStatus.NOT_FOUND, "not_found", ex.getMessage());
    }

    @ExceptionHandler(InvalidAdminOperationException.class)
    public ResponseEntity<Map<String, String>> invalidAdminOperation(InvalidAdminOperationException ex) {
        return error(HttpStatus.BAD_REQUEST, "invalid_operation", ex.getMessage());
    }

    @ExceptionHandler(DataIntegrityViolationException.class)
    public ResponseEntity<Map<String, String>> integrityViolation() {
        return error(HttpStatus.CONFLICT, "conflict", "The requested change conflicts with existing data.");
    }

    @ExceptionHandler(InvalidXrayException.class)
    public ResponseEntity<Map<String, String>> invalidXray(InvalidXrayException ex) {
        return error(HttpStatus.UNPROCESSABLE_ENTITY, "invalid_input_image", ex.getMessage());
    }

    @ExceptionHandler({UploadTooLargeException.class, MaxUploadSizeExceededException.class})
    public ResponseEntity<Map<String, String>> uploadTooLarge() {
        return error(HttpStatus.PAYLOAD_TOO_LARGE, "file_too_large", "The image exceeds the 5 MiB upload limit.");
    }

    @ExceptionHandler(MlServiceException.class)
    public ResponseEntity<Map<String, String>> mlServiceFailure(MlServiceException ex) {
        return error(ex.getStatus(), ex.getErrorCode(), ex.getMessage());
    }

    @ExceptionHandler(AssessmentNotFoundException.class)
    public ResponseEntity<Map<String, String>> assessmentNotFound() {
        return error(HttpStatus.NOT_FOUND, "not_found", "Assessment not found.");
    }

    @ExceptionHandler(AssessmentUserUnavailableException.class)
    public ResponseEntity<Map<String, String>> assessmentUserUnavailable() {
        return error(HttpStatus.UNAUTHORIZED, "unauthorized", "Authentication required.");
    }

    private static ResponseEntity<Map<String, String>> error(HttpStatus status, String code, String message) {
        return ResponseEntity.status(status).body(Map.of("error", code, "message", message));
    }
}
