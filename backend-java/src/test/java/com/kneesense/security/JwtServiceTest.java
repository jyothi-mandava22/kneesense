package com.kneesense.security;

import io.jsonwebtoken.Claims;
import io.jsonwebtoken.Jwts;
import io.jsonwebtoken.security.Keys;
import org.junit.jupiter.api.Test;

import java.nio.charset.StandardCharsets;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNull;

class JwtServiceTest {

    private static final String TEST_SECRET = "test-only-secret-that-is-at-least-32-bytes-long";

    @Test
    void tokenContainsIdentityAndTimesButNoRole() {
        JwtService service = new JwtService(TEST_SECRET, 3_600_000L);
        String token = service.createToken("patient@example.com");

        Claims claims = Jwts.parser()
            .verifyWith(Keys.hmacShaKeyFor(TEST_SECRET.getBytes(StandardCharsets.UTF_8)))
            .build()
            .parseSignedClaims(token)
            .getPayload();

        assertEquals("patient@example.com", claims.getSubject());
        assertEquals("patient@example.com", service.extractSubject(token));
        assertNull(claims.get("role"));
    }
}
