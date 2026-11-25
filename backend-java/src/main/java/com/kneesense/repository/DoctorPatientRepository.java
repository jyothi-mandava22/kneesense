package com.kneesense.repository;

import com.kneesense.domain.DoctorPatient;
import com.kneesense.domain.DoctorPatientId;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;

import java.util.List;

public interface DoctorPatientRepository extends JpaRepository<DoctorPatient, DoctorPatientId> {

    @Query("select assignment from DoctorPatient assignment where assignment.doctor.id = :doctorId")
    List<DoctorPatient> findAllForDoctor(@Param("doctorId") Long doctorId);

    @Query("select case when count(assignment) > 0 then true else false end " +
           "from DoctorPatient assignment " +
           "where assignment.doctor.id = :doctorId and assignment.patient.id = :patientId")
    boolean existsAssignment(@Param("doctorId") Long doctorId,
                             @Param("patientId") Long patientId);
}
