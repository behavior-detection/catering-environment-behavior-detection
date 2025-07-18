package com.handy.ocr.service;


import com.handy.ocr.vo.accurategeneral.AccurateGeneralVo;
import com.handy.ocr.vo.businesslicense.BusinessLicenseVo;
import com.handy.ocr.vo.idcardback.IdCardBackVo;
import com.handy.ocr.vo.idcardfront.IdCardFrontVo;

/**
 * @author hanshuai
 * @Description: {百度ocr接口}
 * @date 2019/9/10
 */
public interface IBaiDuOcrService {

    /**
     * 营业执照识别
     *
     * @param image 图片路径
     * @param file  Base64编码
     * @return
     */
    BusinessLicenseVo businessLicense(String image, byte[] file);

    /**
     * 身份证正面识别
     *
     * @param image 图片路径
     * @param file  Base64编码
     * @return
     */
    IdCardFrontVo idCardFront(String image, byte[] file);

    /**
     * 身份证背面识别
     *
     * @param image 图片路径
     * @param file  Base64编码
     * @return
     */
    IdCardBackVo idCardBack(String image, byte[] file);

    /**
     * 通用文字识别(含位置高精度版本)
     *
     * @param image 图片路径
     * @param file  Base64编码
     * @return
     */
    AccurateGeneralVo accurateGeneral(String image, byte[] file);
}
