package com.kneesense.ml;

import org.springframework.http.HttpStatus;

import java.util.Locale;

/** Safe application-level error raised when the upstream prediction service fails. */
public class MlServiceException extends RuntimeException {

    private final String errorCode;
    private final HttpStatus status;

    public MlServiceException(String errorCode, HttpStatus status, String safeMessage) {
        super(safeMessage);
        this.errorCode = errorCode;
        this.status = status;
    }

    public String getErrorCode() {
        return errorCode;
    }

    public HttpStatus getStatus() {
        return status;
    }

    public static MlServiceException forCode(String code) {
        String normalized = code == null ? "internal_error" : code.trim().toLowerCase(Locale.ROOT);
        return switch (normalized) {
            case "invalid_input_image" -> new MlServiceException(
                "invalid_input_image", HttpStatus.UNPROCESSABLE_ENTITY,
                "The image could not be processed. Upload a valid knee X-ray in PNG or JPEG format."
            );
            case "rate_limited" -> new MlServiceException(
                "rate_limited", HttpStatus.TOO_MANY_REQUESTS,
                "Prediction capacity is temporarily limited. Please retry shortly."
            );
            case "model_unavailable" -> new MlServiceException(
                "model_unavailable", HttpStatus.SERVICE_UNAVAILABLE,
                "The prediction service is waking up. Please retry shortly."
            );
            case "unauthorized" -> new MlServiceException(
                "model_unavailable", HttpStatus.SERVICE_UNAVAILABLE,
                "The prediction service is temporarily unavailable. Please retry later."
            );
            default -> new MlServiceException(
                "internal_error", HttpStatus.INTERNAL_SERVER_ERROR,
                "Prediction could not be completed. Please try again."
            );
        };
    }
}
