package com.kneesense.api.doctor;

import com.kneesense.api.doctor.dto.DoctorAssessmentDetailResponse;
import com.kneesense.api.doctor.dto.DoctorAssessmentHistoryResponse;
import com.kneesense.api.doctor.dto.DoctorPatientResponse;
import com.kneesense.domain.AssessmentResult;
import com.kneesense.domain.DoctorPatient;
import com.kneesense.domain.Report;
import com.kneesense.repository.AssessmentResultRepository;
import com.kneesense.repository.DoctorPatientRepository;
import com.kneesense.repository.ReportRepository;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.util.List;
import java.util.Locale;

@Service
public class DoctorService {

    private final DoctorPatientRepository doctorPatientRepository;
    private final AssessmentResultRepository assessmentResultRepository;
    private final ReportRepository reportRepository;

    public DoctorService(
        DoctorPatientRepository doctorPatientRepository,
        AssessmentResultRepository assessmentResultRepository,
        ReportRepository reportRepository
    ) {
        this.doctorPatientRepository = doctorPatientRepository;
        this.assessmentResultRepository = assessmentResultRepository;
        this.reportRepository = reportRepository;
    }

    @Transactional(readOnly = true)
    public List<DoctorPatientResponse> listAssignedPatients(Long doctorId) {
        return doctorPatientRepository.findAllForDoctor(doctorId).stream()
            .map(DoctorService::toPatientResponse)
            .toList();
    }

    @Transactional(readOnly = true)
    public List<DoctorAssessmentHistoryResponse> listPatientAssessments(Long doctorId, Long patientId) {
        requireAssignment(doctorId, patientId);

        return assessmentResultRepository.findAllByUpload_User_IdOrderByCreatedAtDesc(patientId).stream()
            .map(DoctorService::toHistoryResponse)
            .toList();
    }

    @Transactional(readOnly = true)
    public DoctorAssessmentDetailResponse getPatientAssessment(
        Long doctorId,
        Long patientId,
        Long resultId
    ) {
        requireAssignment(doctorId, patientId);

        AssessmentResult result = assessmentResultRepository.findByIdAndUpload_User_Id(resultId, patientId)
            .orElseThrow(() -> new DoctorResourceNotFoundException("Assessment not found."));

        Report report = reportRepository.findByResult_IdAndResult_Upload_User_Id(resultId, patientId)
            .orElseThrow(() -> new DoctorResourceNotFoundException("Assessment report not found."));

        return toDetailResponse(result, report);
    }

    private void requireAssignment(Long doctorId, Long patientId) {
        if (!doctorPatientRepository.existsAssignment(doctorId, patientId)) {
            // The same 404 is returned for an unknown patient and an unassigned patient.
            throw new DoctorResourceNotFoundException("Patient not found.");
        }
    }

    private static DoctorPatientResponse toPatientResponse(DoctorPatient assignment) {
    return new DoctorPatientResponse(
        assignment.getPatient().getId(),
        assignment.getPatient().getFullName(),
        assignment.getPatient().getEmail(),
        assignment.getAssignedAt()
    );
}

    private static DoctorAssessmentHistoryResponse toHistoryResponse(AssessmentResult result) {
        return new DoctorAssessmentHistoryResponse(
            result.getId(),
            result.getKlGrade().intValue(),
            result.getConfidence(),
            result.getSource().name().toLowerCase(Locale.ROOT),
            result.getCreatedAt()
        );
    }

    private static DoctorAssessmentDetailResponse toDetailResponse(AssessmentResult result, Report report) {
    return new DoctorAssessmentDetailResponse(
        result.getId(),
        result.getUpload().getUser().getId(),
        result.getUpload().getUser().getFullName(),
        result.getUpload().getUser().getEmail(),
        result.getKlGrade().intValue(),
        result.getConfidence(),
        result.getSource().name().toLowerCase(Locale.ROOT),
        result.getCreatedAt(),
        report.getClinicianText()
    );
}
}
