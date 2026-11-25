package com.kneesense.domain;

import jakarta.persistence.EmbeddedId;
import jakarta.persistence.Entity;
import jakarta.persistence.FetchType;
import jakarta.persistence.JoinColumn;
import jakarta.persistence.ManyToOne;
import jakarta.persistence.MapsId;
import jakarta.persistence.Table;
import org.hibernate.annotations.CreationTimestamp;

import jakarta.persistence.Column;
import java.time.LocalDateTime;

@Entity
@Table(name = "doctor_patient")
public class DoctorPatient {

    @EmbeddedId
    private DoctorPatientId id;

    @MapsId("doctorId")
    @ManyToOne(fetch = FetchType.LAZY, optional = false)
    @JoinColumn(name = "doctor_id", nullable = false)
    private User doctor;

    @MapsId("patientId")
    @ManyToOne(fetch = FetchType.LAZY, optional = false)
    @JoinColumn(name = "patient_id", nullable = false)
    private User patient;

    @CreationTimestamp
    @Column(name = "assigned_at", nullable = false, updatable = false, columnDefinition = "TIMESTAMP(6)")
    private LocalDateTime assignedAt;

    protected DoctorPatient() {
        // Required by JPA.
    }

    public DoctorPatient(User doctor, User patient) {
        this.doctor = doctor;
        this.patient = patient;
        this.id = new DoctorPatientId(doctor.getId(), patient.getId());
    }

    public DoctorPatientId getId() {
        return id;
    }

    public User getDoctor() {
        return doctor;
    }

    public User getPatient() {
        return patient;
    }

    public LocalDateTime getAssignedAt() {
        return assignedAt;
    }
}
