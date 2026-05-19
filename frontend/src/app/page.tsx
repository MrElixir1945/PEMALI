import NavBar from "@/components/NavBar";
import HeroSection from "@/components/pemali/HeroSection";
import PhilosophySection from "@/components/pemali/PhilosophySection";
import LoopSection from "@/components/pemali/LoopSection";
import ArchitectureSection from "@/components/pemali/ArchitectureSection";
import CTASection from "@/components/pemali/CTASection";

export default function Home() {
  return (
    <main className="flex-1 noise-overlay">
      <NavBar />
      <HeroSection />
      <PhilosophySection />
      <LoopSection />
      <ArchitectureSection />
      <CTASection />
    </main>
  );
}
