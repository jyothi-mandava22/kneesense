package com.kneesense.api.assessment.service;

import com.github.benmanes.caffeine.cache.Cache;
import com.github.benmanes.caffeine.cache.Caffeine;
import io.github.bucket4j.Bucket;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;

import java.time.Duration;

@Service
public class LiveReportRateLimiter {

    private final Cache<Long, Bucket> buckets;
    private final long capacity;
    private final Duration refillPeriod;

    public LiveReportRateLimiter(
        @Value("${app.rate-limit.assessment.capacity:10}") long capacity,
        @Value("${app.rate-limit.assessment.refill-period:PT24H}") Duration refillPeriod
    ) {
        if (capacity < 1 || refillPeriod == null || refillPeriod.isZero() || refillPeriod.isNegative()) {
            throw new IllegalArgumentException("Assessment rate-limit settings must be positive.");
        }

        this.capacity = capacity;
        this.refillPeriod = refillPeriod;

        this.buckets = Caffeine.newBuilder()
            .maximumSize(100_000)
            .expireAfterAccess(Duration.ofDays(2))
            .build();
    }

    /**
     * Returns true when this user's live-report allowance is exhausted.
     * The assessment itself must still continue using cached reports.
     */
    public boolean shouldForceCachedReports(Long userId) {
        if (userId == null || userId < 1) {
            throw new IllegalArgumentException("A valid user ID is required.");
        }

        Bucket bucket = buckets.get(userId, ignored ->
            Bucket.builder()
                .addLimit(limit -> limit.capacity(capacity).refillGreedy(capacity, refillPeriod))
                .build()
        );

        return !bucket.tryConsume(1);
    }
}