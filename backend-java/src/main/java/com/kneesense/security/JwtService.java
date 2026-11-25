package com.kneesense.security;

import io.jsonwebtoken.Claims;
import io.jsonwebtoken.Jwts;
import io.jsonwebtoken.security.Keys;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;

import javax.crypto.SecretKey;
import java.nio.charset.StandardCharsets;
import java.time.Duration;
import java.time.Instant;
import java.util.Date;

@Service
public class JwtService {

    private final SecretKey signingKey;
    private final Duration tokenLifetime;

    public JwtService(
        @Value("${app.jwt.secret}") String secret,
        @Value("${app.jwt.ttl-ms:43200000}") long ttlMillis
    ) {
        byte[] secretBytes = secret == null ? new byte[0] : secret.getBytes(StandardCharsets.UTF_8);
        if (secretBytes.length < 32) {
            throw new IllegalStateException("JWT_SECRET must contain at least 32 UTF-8 bytes.");
        }
        if (ttlMillis < 60_000L) {
            throw new IllegalStateException("JWT_EXPIRATION_MS must be at least 60000.");
        }
        this.signingKey = Keys.hmacShaKeyFor(secretBytes);
        this.tokenLifetime = Duration.ofMillis(ttlMillis);
    }

    /** The token contains identity and timestamps only; role is deliberately not included. */
    public String createToken(String email) {
        Instant issuedAt = Instant.now();
        Instant expiresAt = issuedAt.plus(tokenLifetime);
        return Jwts.builder()
            .subject(email)
            .issuedAt(Date.from(issuedAt))
            .expiration(Date.from(expiresAt))
            .signWith(signingKey)
            .compact();
    }

    public String extractSubject(String token) {
        Claims claims = Jwts.parser()
            .verifyWith(signingKey)
            .build()
            .parseSignedClaims(token)
            .getPayload();
        return claims.getSubject();
    }

    public Duration getTokenLifetime() {
        return tokenLifetime;
    }
}
