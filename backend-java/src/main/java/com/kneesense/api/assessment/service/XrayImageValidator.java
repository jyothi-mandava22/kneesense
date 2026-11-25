package com.kneesense.api.assessment.service;

import com.kneesense.api.assessment.exception.InvalidXrayException;
import com.kneesense.api.assessment.exception.UploadTooLargeException;
import org.springframework.stereotype.Component;
import org.springframework.web.multipart.MultipartFile;
import org.springframework.http.MediaType;

import java.io.IOException;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.util.HexFormat;

/** Validates file bytes in memory; no uploaded image is written to disk or logged. */
@Component
public class XrayImageValidator {

    public static final long MAX_IMAGE_BYTES = 5L * 1024L * 1024L;

    private static final byte[] PNG_SIGNATURE = {
        (byte) 0x89, 0x50, 0x4E, 0x47, 0x0D, 0x0A, 0x1A, 0x0A
    };

    public ValidatedXray validate(MultipartFile file) {
        if (file == null || file.isEmpty()) {
            throw new InvalidXrayException("Choose a PNG or JPEG knee X-ray before submitting.");
        }
        if (file.getSize() > MAX_IMAGE_BYTES) {
            throw new UploadTooLargeException();
        }

        final byte[] bytes;
        try {
            bytes = file.getBytes();
        } catch (IOException ex) {
            throw new InvalidXrayException("The uploaded image could not be read. Please try again.");
        }

        MediaType detectedType;
        String filename;
        if (hasPngSignature(bytes)) {
            detectedType = MediaType.IMAGE_PNG;
            filename = "kneesense-upload.png";
        } else if (hasJpegSignature(bytes)) {
            detectedType = MediaType.IMAGE_JPEG;
            filename = "kneesense-upload.jpg";
        } else {
            throw new InvalidXrayException("Only PNG and JPEG image files are accepted.");
        }

        return new ValidatedXray(bytes, detectedType, filename, sha256(bytes));
    }

    private static boolean hasPngSignature(byte[] bytes) {
        if (bytes.length < PNG_SIGNATURE.length) {
            return false;
        }
        for (int i = 0; i < PNG_SIGNATURE.length; i++) {
            if (bytes[i] != PNG_SIGNATURE[i]) {
                return false;
            }
        }
        return true;
    }

    private static boolean hasJpegSignature(byte[] bytes) {
        return bytes.length >= 3
            && (bytes[0] & 0xFF) == 0xFF
            && (bytes[1] & 0xFF) == 0xD8
            && (bytes[2] & 0xFF) == 0xFF;
    }

    private static String sha256(byte[] bytes) {
        try {
            return HexFormat.of().formatHex(MessageDigest.getInstance("SHA-256").digest(bytes));
        } catch (NoSuchAlgorithmException ex) {
            throw new IllegalStateException("SHA-256 is not available in this Java runtime.", ex);
        }
    }
}
