package com.handy.ocr.service.impl;

import com.alibaba.fastjson.JSON;
import com.baidu.aip.ocr.AipOcr;
import com.handy.ocr.service.IBaiDuOcrService;
import com.handy.ocr.vo.accurategeneral.AccurateGeneralVo;
import com.handy.ocr.vo.businesslicense.BusinessLicenseVo;
import com.handy.ocr.vo.idcardback.IdCardBackVo;
import com.handy.ocr.vo.idcardfront.IdCardFrontVo;
import lombok.val;
import org.json.JSONObject;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;

import java.util.HashMap;

/**
 * @author hanshuai
 * @Description: {百度ocr接口}
 * @date 2019/9/10
 */
@Service("baiDuOcrService")
public class BaiDuOcrServiceImpl implements IBaiDuOcrService {
    @Value("${baidu_ocr_app_id}")
    private String APP_ID;
    @Value("${baidu_ocr_api_key}")
    private String API_KEY;
    @Value("${baidu_ocr_secret_key}")
    private String SECRET_KEY;

    /**
     * 营业执照识别
     *
     * @param image 图片路径
     * @param file  Base64编码
     * @return
     */
    @Override
    public BusinessLicenseVo businessLicense(String image, byte[] file) {
        // 初始化一个AipOcr
        AipOcr client = new AipOcr(APP_ID, API_KEY, SECRET_KEY);
        // 传入可选参数调用接口
        HashMap<String, String> options = new HashMap<String, String>();
        String json = "";
        if (image != null) {
            // 参数为本地图片路径
            JSONObject res = client.businessLicense(image, options);
            json = res.toString(2);
        }
        if (file != null) {
            // 参数为本地图片二进制数组
            JSONObject res = client.businessLicense(file, options);
            json = res.toString(2);
        }
        String newJson = json.replace("社会信用代码", "socialCreditCode")
                .replace("组成形式", "composingForm")
                .replace("经营范围", "businessScope")
                .replace("法人", "legalPerson")
                .replace("成立日期", "establishmentDate")
                .replace("注册资本", "registeredCapital")
                .replace("证件编号", "certificateNumber")
                .replace("地址", "site")
                .replace("单位名称", "organizationName")
                .replace("类型", "type")
                .replace("有效期", "validityPeriod");
        val businessLicenseVo = JSON.parseObject(newJson, BusinessLicenseVo.class);
        return businessLicenseVo;
    }

    /**
     * 身份证正面识别
     *
     * @param image 图片路径
     * @param file  Base64编码
     * @return
     */
    @Override
    public IdCardFrontVo idCardFront(String image, byte[] file) {
        // 初始化一个AipOcr
        AipOcr client = new AipOcr(APP_ID, API_KEY, SECRET_KEY);
        // 传入可选参数调用接口
        HashMap<String, String> options = new HashMap<String, String>();
        //是否检测图像朝向
        options.put("detect_direction", "true");
        //是否开启身份证风险类型(身份证复印件、临时身份证、身份证翻拍、修改过的身份证)功能，
        // 默认不开启，即：false。可选值:true-开启；false-不开启
        options.put("detect_risk", "false");

        String json = "";
        if (image != null) {
            // 参数为本地图片路径
            JSONObject res = client.idcard(image, "front", options);
            json = res.toString(2);
        }
        if (file != null) {
            // 参数为本地图片二进制数组
            JSONObject res = client.idcard(file, "front", options);
            json = res.toString(2);
        }

        String newJson = json.replace("姓名", "name")
                .replace("民族", "nation")
                .replace("住址", "address")
                .replace("公民身份号码", "citizenIdNumber")
                .replace("出生", "birth")
                .replace("性别", "sex");

        val idCardFrontVo = JSON.parseObject(newJson, IdCardFrontVo.class);
        return idCardFrontVo;
    }

    /**
     * 身份证背面识别
     *
     * @param image 图片路径
     * @param file  Base64编码
     * @return
     */
    @Override
    public IdCardBackVo idCardBack(String image, byte[] file) {
        // 初始化一个AipOcr
        AipOcr client = new AipOcr(APP_ID, API_KEY, SECRET_KEY);
        // 传入可选参数调用接口
        HashMap<String, String> options = new HashMap<String, String>();
        //是否检测图像朝向
        options.put("detect_direction", "true");
        //是否开启身份证风险类型(身份证复印件、临时身份证、身份证翻拍、修改过的身份证)功能，
        // 默认不开启，即：false。可选值:true-开启；false-不开启
        options.put("detect_risk", "false");

        String json = "";
        if (image != null) {
            // 参数为本地图片路径
            JSONObject res = client.idcard(image, "back", options);
            json = res.toString(2);
        }
        if (file != null) {
            // 参数为本地图片二进制数组
            JSONObject res = client.idcard(file, "back", options);
            json = res.toString(2);
        }

        String newJson = json.replace("失效日期", "expiryDate")
                .replace("签发机关", "issuingSuthority")
                .replace("签发日期", "issuingDate");
        val idCardBackVo = JSON.parseObject(newJson, IdCardBackVo.class);
        return idCardBackVo;
    }

    /**
     * 通用文字识别(含位置高精度版本)
     *
     * @param image 图片路径
     * @param file  Base64编码
     * @return
     */
    @Override
    public AccurateGeneralVo accurateGeneral(String image, byte[] file) {
        // 初始化一个AipOcr
        AipOcr client = new AipOcr(APP_ID, API_KEY, SECRET_KEY);

        // 传入可选参数调用接口
        HashMap<String, String> options = new HashMap<String, String>();
        options.put("recognize_granularity", "big");
        options.put("detect_direction", "true");
        options.put("vertexes_location", "true");
        options.put("probability", "false");

        String json = "";
        if (image != null) {
            // 参数为本地图片路径
            JSONObject res = client.accurateGeneral(image, options);
            json = res.toString(2);
        }
        if (file != null) {
            // 参数为本地图片二进制数组
            JSONObject res = client.accurateGeneral(file, options);
            json = res.toString(2);
        }
        val accurateGeneralVo = JSON.parseObject(json, AccurateGeneralVo.class);
        return accurateGeneralVo;
    }
}
