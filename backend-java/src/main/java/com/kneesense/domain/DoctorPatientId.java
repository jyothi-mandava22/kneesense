package com.kneesense.domain;

import jakarta.persistence.Column;
import jakarta.persistence.Embeddable;

import java.io.Serializable;
import java.util.Objects;

@Embeddable
public class DoctorPatientId implements Serializable {

    @Column(name = "doctor_id", columnDefinition = "BIGINT UNSIGNED")
    private Long doctorId;

    @Column(name = "patient_id", columnDefinition = "BIGINT UNSIGNED")
    private Long patientId;

    public DoctorPatientId() {
        // Required by JPA.
    }

    public DoctorPatientId(Long doctorId, Long patientId) {
        this.doctorId = doctorId;
        this.patientId = patientId;
    }

    public Long getDoctorId() {
        return doctorId;
    }

    public Long getPatientId() {
        return patientId;
    }

    @Override
    public boolean equals(Object other) {
        if (this == other) return true;
        if (!(other instanceof DoctorPatientId that)) return false;
        return Objects.equals(doctorId, that.doctorId)
            && Objects.equals(patientId, that.patientId);
    }

    @Override
    public int hashCode() {
        return Objects.hash(doctorId, patientId);
    }
}
