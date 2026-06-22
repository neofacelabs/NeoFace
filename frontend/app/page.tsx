import { Navbar } from "@/components/layout/Navbar";
import { HeroSection } from "@/components/landing/HeroSection";
import { ScrollStory } from "@/components/landing/ScrollStory";
import { ModalitiesSection } from "@/components/landing/ModalitiesSection";
import { ProductSection } from "@/components/landing/ProductSection";
import { DeveloperSection } from "@/components/landing/DeveloperSection";
import { SecuritySection } from "@/components/landing/SecuritySection";
import { ArchitectureSection } from "@/components/landing/ArchitectureSection";
import { FinalCTA } from "@/components/landing/FinalCTA";
import { Footer } from "@/components/layout/Footer";

export default function HomePage() {
  return (
    <main className="relative bg-black min-h-screen">
      <Navbar />
      <HeroSection />
      <ScrollStory />
      <ModalitiesSection />
      <ProductSection />
      <DeveloperSection />
      <SecuritySection />
      <ArchitectureSection />
      <FinalCTA />
      <Footer />
    </main>
  );
}
