package com.kneesense.domain;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.FetchType;
import jakarta.persistence.GeneratedValue;
import jakarta.persistence.GenerationType;
import jakarta.persistence.Id;
import jakarta.persistence.JoinColumn;
import jakarta.persistence.OneToOne;
import jakarta.persistence.Table;
import jakarta.persistence.UniqueConstraint;
import org.hibernate.annotations.CreationTimestamp;
import org.hibernate.annotations.JdbcTypeCode;
import org.hibernate.type.SqlTypes;

import java.time.LocalDateTime;

@Entity
@Table(
    name = "reports",
    uniqueConstraints = @UniqueConstraint(name = "result_id", columnNames = "result_id")
)
public class Report {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    @Column(name = "id", columnDefinition = "BIGINT UNSIGNED")
    private Long id;

    @OneToOne(fetch = FetchType.LAZY, optional = false)
    @JoinColumn(name = "result_id", nullable = false, unique = true)
    private AssessmentResult result;

    @JdbcTypeCode(SqlTypes.LONGVARCHAR)
    @Column(name = "clinician_text", nullable = false, columnDefinition = "LONGTEXT")
    private String clinicianText;

    @JdbcTypeCode(SqlTypes.LONGVARCHAR)
    @Column(name = "patient_text", nullable = false, columnDefinition = "LONGTEXT")
    private String patientText;

    @CreationTimestamp
    @Column(name = "created_at", nullable = false, updatable = false, columnDefinition = "TIMESTAMP(6)")
    private LocalDateTime createdAt;

    protected Report() {
        // Required by JPA.
    }

    public Report(AssessmentResult result, String clinicianText, String patientText) {
        this.result = result;
        this.clinicianText = clinicianText;
        this.patientText = patientText;
    }

    public Long getId() {
        return id;
    }

    public AssessmentResult getResult() {
        return result;
    }

    public String getClinicianText() {
        return clinicianText;
    }

    public String getPatientText() {
        return patientText;
    }

    public LocalDateTime getCreatedAt() {
        return createdAt;
    }
}
