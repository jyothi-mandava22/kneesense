package com.kneesense.api.doctor;

import com.kneesense.api.doctor.dto.DoctorAssessmentDetailResponse;
import com.kneesense.api.doctor.dto.DoctorAssessmentHistoryResponse;
import com.kneesense.api.doctor.dto.DoctorPatientResponse;
import com.kneesense.security.AppUserPrincipal;
import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import java.util.List;

@RestController
@RequestMapping("/api/doctor")
public class DoctorController {

    private final DoctorService doctorService;

    public DoctorController(DoctorService doctorService) {
        this.doctorService = doctorService;
    }

    @GetMapping("/patients")
    public List<DoctorPatientResponse> assignedPatients(
        @AuthenticationPrincipal AppUserPrincipal principal
    ) {
        return doctorService.listAssignedPatients(principal.getId());
    }

    @GetMapping("/patients/{patientId}/assessments")
    public List<DoctorAssessmentHistoryResponse> patientAssessments(
        @AuthenticationPrincipal AppUserPrincipal principal,
        @PathVariable Long patientId
    ) {
        return doctorService.listPatientAssessments(principal.getId(), patientId);
    }

    @GetMapping("/patients/{patientId}/assessments/{resultId}")
    public DoctorAssessmentDetailResponse patientAssessment(
        @AuthenticationPrincipal AppUserPrincipal principal,
        @PathVariable Long patientId,
        @PathVariable Long resultId
    ) {
        return doctorService.getPatientAssessment(principal.getId(), patientId, resultId);
    }
}
