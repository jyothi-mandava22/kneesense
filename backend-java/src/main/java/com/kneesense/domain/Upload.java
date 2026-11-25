package com.kneesense.domain;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.FetchType;
import jakarta.persistence.GeneratedValue;
import jakarta.persistence.GenerationType;
import jakarta.persistence.Id;
import jakarta.persistence.JoinColumn;
import jakarta.persistence.ManyToOne;
import jakarta.persistence.Table;
import jakarta.persistence.Index;
import org.hibernate.annotations.CreationTimestamp;

import java.time.LocalDateTime;

@Entity
@Table(
    name = "uploads",
    indexes = @Index(name = "idx_uploads_user_created", columnList = "user_id, created_at")
)
public class Upload {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    @Column(name = "id", columnDefinition = "BIGINT UNSIGNED")
    private Long id;

    @ManyToOne(fetch = FetchType.LAZY, optional = false)
    @JoinColumn(name = "user_id", nullable = false)
    private User user;

    @Column(name = "content_hash", nullable = false, length = 64, columnDefinition = "CHAR(64)")
    private String contentHash;

    @CreationTimestamp
    @Column(name = "created_at", nullable = false, updatable = false, columnDefinition = "TIMESTAMP(6)")
    private LocalDateTime createdAt;

    protected Upload() {
        // Required by JPA.
    }

    public Upload(User user, String contentHash) {
        this.user = user;
        this.contentHash = contentHash;
    }

    public Long getId() {
        return id;
    }

    public User getUser() {
        return user;
    }

    public String getContentHash() {
        return contentHash;
    }

    public LocalDateTime getCreatedAt() {
        return createdAt;
    }
}
