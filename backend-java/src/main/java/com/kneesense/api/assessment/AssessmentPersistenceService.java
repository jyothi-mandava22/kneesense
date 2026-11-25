package com.kneesense.api.assessment;

import com.kneesense.api.assessment.exception.AssessmentUserUnavailableException;
import com.kneesense.domain.AssessmentResult;
import com.kneesense.domain.PredictionSource;
import com.kneesense.domain.Report;
import com.kneesense.domain.Upload;
import com.kneesense.domain.User;
import com.kneesense.ml.MlPredictionResponse;
import com.kneesense.repository.AssessmentResultRepository;
import com.kneesense.repository.ReportRepository;
import com.kneesense.repository.UploadRepository;
import com.kneesense.repository.UserRepository;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.LocalDateTime;
import java.util.Locale;

/** Saves assessment metadata and reports atomically after ML inference succeeds. */
@Service
public class AssessmentPersistenceService {

    private final UserRepository userRepository;
    private final UploadRepository uploadRepository;
    private final AssessmentResultRepository assessmentResultRepository;
    private final ReportRepository reportRepository;

    public AssessmentPersistenceService(
        UserRepository userRepository,
        UploadRepository uploadRepository,
        AssessmentResultRepository assessmentResultRepository,
        ReportRepository reportRepository
    ) {
        this.userRepository = userRepository;
        this.uploadRepository = uploadRepository;
        this.assessmentResultRepository = assessmentResultRepository;
        this.reportRepository = reportRepository;
    }

    @Transactional
    public SavedAssessment save(Long userId, String contentHash, MlPredictionResponse prediction) {
        User user = userRepository.findById(userId)
            .orElseThrow(AssessmentUserUnavailableException::new);

        Upload upload = uploadRepository.saveAndFlush(new Upload(user, contentHash));
        PredictionSource source = PredictionSource.valueOf(prediction.source().toUpperCase(Locale.ROOT));
        AssessmentResult result = assessmentResultRepository.saveAndFlush(new AssessmentResult(
            upload,
            (byte) prediction.klGrade(),
            prediction.confidence(),
            source
        ));
        reportRepository.saveAndFlush(new Report(
            result,
            prediction.clinicianReport(),
            prediction.patientReport()
        ));

        return new SavedAssessment(result.getId(), result.getCreatedAt());
    }

    public record SavedAssessment(Long resultId, LocalDateTime createdAt) {
    }
}
