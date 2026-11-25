package com.kneesense.domain;

import jakarta.persistence.Column;
import jakarta.persistence.Convert;
import jakarta.persistence.Entity;
import jakarta.persistence.FetchType;
import jakarta.persistence.GeneratedValue;
import jakarta.persistence.GenerationType;
import jakarta.persistence.Id;
import jakarta.persistence.JoinColumn;
import jakarta.persistence.ManyToOne;
import jakarta.persistence.Table;
import jakarta.persistence.UniqueConstraint;
import org.hibernate.annotations.CreationTimestamp;
import org.hibernate.annotations.JdbcTypeCode;
import org.hibernate.type.SqlTypes;

import java.math.BigDecimal;
import java.time.LocalDateTime;

@Entity
@Table(
    name = "results",
    uniqueConstraints = @UniqueConstraint(name = "upload_id", columnNames = "upload_id")
)
public class AssessmentResult {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    @Column(name = "id", columnDefinition = "BIGINT UNSIGNED")
    private Long id;

    @ManyToOne(fetch = FetchType.LAZY, optional = false)
    @JoinColumn(name = "upload_id", nullable = false)
    private Upload upload;

    @Column(name = "kl_grade", nullable = false, columnDefinition = "TINYINT UNSIGNED")
    private Byte klGrade;

    @Column(name = "confidence", nullable = false, precision = 8, scale = 6)
    private BigDecimal confidence;

    @Convert(converter = PredictionSourceConverter.class)
    @JdbcTypeCode(SqlTypes.VARCHAR)
    @Column(name = "source", nullable = false, columnDefinition = "ENUM('live','cached')")
    private PredictionSource source;

    @CreationTimestamp
    @Column(name = "created_at", nullable = false, updatable = false, columnDefinition = "TIMESTAMP(6)")
    private LocalDateTime createdAt;

    protected AssessmentResult() {
        // Required by JPA.
    }

    public AssessmentResult(Upload upload, Byte klGrade, BigDecimal confidence, PredictionSource source) {
        this.upload = upload;
        this.klGrade = klGrade;
        this.confidence = confidence;
        this.source = source;
    }

    public Long getId() {
        return id;
    }

    public Upload getUpload() {
        return upload;
    }

    public Byte getKlGrade() {
        return klGrade;
    }

    public BigDecimal getConfidence() {
        return confidence;
    }

    public PredictionSource getSource() {
        return source;
    }

    public LocalDateTime getCreatedAt() {
        return createdAt;
    }
}
