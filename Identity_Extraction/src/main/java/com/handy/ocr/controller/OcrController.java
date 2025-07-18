package main.java.com.handy.ocr.controller;

import com.handy.ocr.service.IBaiDuOcrService;
import com.handy.ocr.vo.idcardfront.IdCardFrontVo;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.multipart.MultipartFile;

import java.util.HashMap;
import java.util.Map;

/**
 * @author hs
 * @Description: OCR识别控制器
 * @date 2019/9/10
 */
@RestController
@RequestMapping("/api/ocr")
@CrossOrigin(origins = "*")
public class OcrController {

    @Autowired
    private IBaiDuOcrService baiDuOcrService;

    /**
     * 身份证正面识别API
     */
    @PostMapping("/idcard-front")
    public ResponseEntity<Map<String, Object>> recognizeIdCardFront(
            @RequestParam("idCard") MultipartFile file) {

        Map<String, Object> response = new HashMap<>();

        try {
            // 验证文件
            if (file.isEmpty()) {
                response.put("success", false);
                response.put("message", "未上传文件");
                return ResponseEntity.badRequest().body(response);
            }

            // 检查文件大小 (5MB限制)
            if (file.getSize() > 5 * 1024 * 1024) {
                response.put("success", false);
                response.put("message", "文件大小超过5MB限制");
                return ResponseEntity.badRequest().body(response);
            }

            // 检查文件类型
            String contentType = file.getContentType();
            if (contentType == null || !contentType.startsWith("image/")) {
                response.put("success", false);
                response.put("message", "请上传图片文件");
                return ResponseEntity.badRequest().body(response);
            }

            // 调用OCR服务识别身份证
            byte[] imageBytes = file.getBytes();
            IdCardFrontVo result = baiDuOcrService.idCardFront(null, imageBytes);

            // 检查识别结果
            if (result == null || result.getWords_result() == null) {
                response.put("success", false);
                response.put("message", "无法识别身份证信息");
                return ResponseEntity.ok(response);
            }

            // 检查图像状态
            if (!"normal".equals(result.getImage_status())) {
                String statusMessage = getStatusMessage(result.getImage_status());
                response.put("success", false);
                response.put("message", statusMessage);
                return ResponseEntity.ok(response);
            }

            // 提取识别到的信息
            Map<String, Object> data = new HashMap<>();

            if (result.getWords_result().getName() != null) {
                data.put("name", result.getWords_result().getName().getWords());
            }

            if (result.getWords_result().getSex() != null) {
                data.put("gender", result.getWords_result().getSex().getWords());
            }

            if (result.getWords_result().getCitizenIdNumber() != null) {
                data.put("idNumber", result.getWords_result().getCitizenIdNumber().getWords());
            }

            if (result.getWords_result().getBirth() != null) {
                data.put("birth", result.getWords_result().getBirth().getWords());
            }

            if (result.getWords_result().getAddress() != null) {
                data.put("address", result.getWords_result().getAddress().getWords());
            }

            if (result.getWords_result().getNation() != null) {
                data.put("nation", result.getWords_result().getNation().getWords());
            }

            // 验证必要字段是否存在
            if (!data.containsKey("name") || !data.containsKey("idNumber")) {
                response.put("success", false);
                response.put("message", "身份证信息不完整，请确保图片清晰");
                return ResponseEntity.ok(response);
            }

            // 返回成功结果
            response.put("success", true);
            response.put("message", "识别成功");
            response.put("data", data);

            return ResponseEntity.ok(response);

        } catch (Exception e) {
            e.printStackTrace();
            response.put("success", false);
            response.put("message", "身份证识别服务异常: " + e.getMessage());
            return ResponseEntity.status(500).body(response);
        }
    }

    /**
     * 获取图像状态对应的中文提示信息
     */
    private String getStatusMessage(String imageStatus) {
        switch (imageStatus) {
            case "reversed_side":
                return "身份证正反面颠倒，请上传身份证正面";
            case "non_idcard":
                return "上传的图片中不包含身份证";
            case "blurred":
                return "身份证图片模糊，请重新拍照";
            case "other_type_card":
                return "检测到其他类型证照，请上传身份证";
            case "over_exposure":
                return "身份证关键字段反光或过曝，请调整光线";
            case "over_dark":
                return "身份证图片过暗，请在光线充足处拍照";
            case "unknown":
                return "图片状态未知，请重新上传";
            default:
                return "身份证识别失败，请检查图片质量";
        }
    }
}