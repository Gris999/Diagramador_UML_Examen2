package generator_uml.back_generator_uml.configuration;

import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.AutoConfigureMockMvc;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.test.web.servlet.MockMvc;

import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.options;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.header;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

// Preflight real contra el filtro CORS de Spring Security, con un origen agregado solo por configuracion.
@SpringBootTest(properties = "app.cors.allowed-origins=https://nuevo.trycloudflare.com")
@AutoConfigureMockMvc
class SecurityConfigurationCorsIntegrationTest {

    @Autowired
    private MockMvc mockMvc;

    @Test
    void preflightDeUnOrigenAgregadoPorConfiguracionEsAceptado() throws Exception {
        mockMvc.perform(options("/generate")
                        .header("Origin", "https://nuevo.trycloudflare.com")
                        .header("Access-Control-Request-Method", "POST")
                        .header("Access-Control-Request-Headers", "content-type"))
                .andExpect(status().isOk())
                .andExpect(header().string("Access-Control-Allow-Origin", "https://nuevo.trycloudflare.com"));
    }

    @Test
    void preflightDeUnOrigenDesconocidoEsRechazado() throws Exception {
        mockMvc.perform(options("/generate")
                        .header("Origin", "https://desconocido.example.com")
                        .header("Access-Control-Request-Method", "POST")
                        .header("Access-Control-Request-Headers", "content-type"))
                .andExpect(status().isForbidden());
    }
}
