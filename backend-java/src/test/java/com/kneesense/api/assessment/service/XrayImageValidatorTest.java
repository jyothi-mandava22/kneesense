package com.kneesense.api.assessment.service;

import com.kneesense.api.assessment.exception.InvalidXrayException;
import com.kneesense.api.assessment.exception.UploadTooLargeException;
import org.junit.jupiter.api.Test;
import org.springframework.mock.web.MockMultipartFile;
import org.springframework.http.MediaType;

import java.util.Arrays;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;

class XrayImageValidatorTest {

    private final XrayImageValidator validator = new XrayImageValidator();

    @Test
    void acceptsPngBasedOnMagicBytesAndCalculatesSha256() {
        byte[] png = {
            (byte) 0x89, 0x50, 0x4E, 0x47, 0x0D, 0x0A, 0x1A, 0x0A, 0x01
        };
        MockMultipartFile file = new MockMultipartFile("file", "scan.bin", "text/plain", png);

        ValidatedXray result = validator.validate(file);

        assertEquals(MediaType.IMAGE_PNG, result.mediaType());
        assertEquals("kneesense-upload.png", result.filename());
        assertEquals(64, result.sha256().length());
        assertTrue(Arrays.equals(png, result.bytes()));
    }

    @Test
    void acceptsJpegBasedOnMagicBytes() {
        byte[] jpeg = {(byte) 0xFF, (byte) 0xD8, (byte) 0xFF, 0x01};
        MockMultipartFile file = new MockMultipartFile("file", "scan.png", "image/png", jpeg);

        ValidatedXray result = validator.validate(file);

        assertEquals(MediaType.IMAGE_JPEG, result.mediaType());
        assertEquals("kneesense-upload.jpg", result.filename());
    }

    @Test
    void rejectsUnsupportedBytesEvenWhenBrowserClaimsPng() {
        MockMultipartFile file = new MockMultipartFile(
            "file", "selfie.png", "image/png", new byte[]{1, 2, 3, 4}
        );

        assertThrows(InvalidXrayException.class, () -> validator.validate(file));
    }

    @Test
    void rejectsEmptyFile() {
        MockMultipartFile file = new MockMultipartFile("file", "empty.png", "image/png", new byte[0]);

        assertThrows(InvalidXrayException.class, () -> validator.validate(file));
    }

    @Test
    void rejectsFilesLargerThanFiveMib() {
        byte[] oversized = new byte[(int) XrayImageValidator.MAX_IMAGE_BYTES + 1];
        MockMultipartFile file = new MockMultipartFile("file", "large.png", "image/png", oversized);

        assertThrows(UploadTooLargeException.class, () -> validator.validate(file));
    }
}
