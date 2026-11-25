package com.kneesense.api.auth;

import com.github.benmanes.caffeine.cache.Cache;
import com.github.benmanes.caffeine.cache.Caffeine;
import io.github.bucket4j.Bucket;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;

import java.time.Duration;

@Service
public class LoginAttemptRateLimiter {

    private final Cache<String, Bucket> buckets;
    private final long capacity;
    private final Duration refillPeriod;

    public LoginAttemptRateLimiter(
        @Value("${app.rate-limit.login.capacity:5}") long capacity,
        @Value("${app.rate-limit.login.refill-period:PT1M}") Duration refillPeriod
    ) {
        if (capacity < 1 || refillPeriod == null || refillPeriod.isZero() || refillPeriod.isNegative()) {
            throw new IllegalArgumentException("Login rate-limit settings must be positive.");
        }

        this.capacity = capacity;
        this.refillPeriod = refillPeriod;

        this.buckets = Caffeine.newBuilder()
            .maximumSize(100_000)
            .expireAfterAccess(Duration.ofMinutes(10))
            .build();
    }

    public boolean allowAttempt(String clientIp) {
        if (clientIp == null || clientIp.isBlank()) {
            throw new IllegalArgumentException("Client IP is required.");
        }

        Bucket bucket = buckets.get(clientIp, ignored ->
            Bucket.builder()
                .addLimit(limit -> limit.capacity(capacity).refillGreedy(capacity, refillPeriod))
                .build()
        );

        return bucket.tryConsume(1);
    }
}