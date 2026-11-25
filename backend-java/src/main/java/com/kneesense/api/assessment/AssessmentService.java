package com.kneesense.api.assessment;

import com.kneesense.api.assessment.dto.AssessmentDetailResponse;
import com.kneesense.api.assessment.dto.AssessmentSummaryResponse;
import com.kneesense.api.assessment.dto.AssessmentUploadResponse;
import com.kneesense.api.assessment.exception.AssessmentNotFoundException;
import com.kneesense.api.assessment.service.ValidatedXray;
import com.kneesense.api.assessment.service.XrayImageValidator;
import com.kneesense.api.assessment.service.LiveReportRateLimiter;
import com.kneesense.domain.AssessmentResult;
import com.kneesense.domain.Report;
import com.kneesense.ml.MlPredictionClient;
import com.kneesense.ml.MlPredictionResponse;
import com.kneesense.repository.AssessmentResultRepository;
import com.kneesense.repository.ReportRepository;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.web.multipart.MultipartFile;

import java.util.Arrays;
import java.util.List;
import java.util.Locale;

@Service
public class AssessmentService {

    private final XrayImageValidator imageValidator;
    private final LiveReportRateLimiter liveReportRateLimiter;
    private final MlPredictionClient predictionClient;
    private final AssessmentPersistenceService persistenceService;
    private final AssessmentResultRepository assessmentResultRepository;
    private final ReportRepository reportRepository;

    public AssessmentService(
        XrayImageValidator imageValidator,
        LiveReportRateLimiter liveReportRateLimiter,
        MlPredictionClient predictionClient,
        AssessmentPersistenceService persistenceService,
        AssessmentResultRepository assessmentResultRepository,
        ReportRepository reportRepository
    ) {
        this.imageValidator = imageValidator;
        this.liveReportRateLimiter = liveReportRateLimiter;
        this.predictionClient = predictionClient;
        this.persistenceService = persistenceService;
        this.assessmentResultRepository = assessmentResultRepository;
        this.reportRepository = reportRepository;
    }

    /**
     * The ML request happens outside a database transaction. Only after a valid
     * prediction returns do we persist upload metadata, result and reports.
     */
    public AssessmentUploadResponse upload(Long userId, MultipartFile file) {
        ValidatedXray image = imageValidator.validate(file);
        try {
            boolean forceCachedReports = liveReportRateLimiter.shouldForceCachedReports(userId);
            MlPredictionResponse prediction = predictionClient.predict(
                image.bytes(), image.mediaType(), image.filename(), forceCachedReports
            );
            AssessmentPersistenceService.SavedAssessment saved = persistenceService.save(
                userId, image.sha256(), prediction
            );

            return new AssessmentUploadResponse(
                saved.resultId(),
                prediction.klGrade(),
                prediction.confidence(),
                prediction.heatmapBase64(),
                prediction.patientReport(),
                prediction.source(),
                saved.createdAt()
            );
        } finally {
            // The request copy is no longer needed after inference/persistence.
            Arrays.fill(image.bytes(), (byte) 0);
        }
    }

    @Transactional(readOnly = true)
    public List<AssessmentSummaryResponse> listMyAssessments(Long userId) {
        return assessmentResultRepository.findAllByUpload_User_IdOrderByCreatedAtDesc(userId).stream()
            .map(AssessmentService::toSummary)
            .toList();
    }

    @Transactional(readOnly = true)
    public AssessmentDetailResponse getMyAssessment(Long userId, Long resultId) {
        AssessmentResult result = assessmentResultRepository.findByIdAndUpload_User_Id(resultId, userId)
            .orElseThrow(AssessmentNotFoundException::new);
        Report report = reportRepository.findByResult_IdAndResult_Upload_User_Id(resultId, userId)
            .orElseThrow(AssessmentNotFoundException::new);

        return new AssessmentDetailResponse(
            result.getId(),
            result.getKlGrade().intValue(),
            result.getConfidence(),
            result.getSource().name().toLowerCase(Locale.ROOT),
            result.getCreatedAt(),
            report.getPatientText()
        );
    }

    private static AssessmentSummaryResponse toSummary(AssessmentResult result) {
        return new AssessmentSummaryResponse(
            result.getId(),
            result.getKlGrade().intValue(),
            result.getConfidence(),
            result.getSource().name().toLowerCase(Locale.ROOT),
            result.getCreatedAt()
        );
    }
}
